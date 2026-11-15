"""Virtual smart bin logic. Fullness is SIMULATED from configured capacity and
estimated waste volume; it is not measured by sensors."""
from datetime import datetime

from flask import current_app
from sqlalchemy import func, update

from ..extensions import db
from ..models import Alert, BinCompartment, CollectionRecord, SmartBin


def create_bin(name, location_id, capacity=None, categories=None):
    cfg = current_app.config
    capacity = capacity or cfg["DEFAULT_COMPARTMENT_CAPACITY"]
    b = SmartBin(name=name, location_id=location_id)
    for cat in categories or cfg["CATEGORIES"]:
        b.compartments.append(BinCompartment(category=cat, max_capacity=capacity))
    db.session.add(b)
    db.session.flush()
    return b


def assign_waste(location_id, category, volume):
    """Reserve room for `volume` litres in the emptiest matching compartment at a location.

    The increment is a single conditional UPDATE executed by the database
    (`current_load = current_load + v WHERE current_load + v <= max_capacity`), so concurrent
    uploads can neither lose updates nor overfill a compartment. Returns the compartment, or
    None when every matching compartment at the location is full. At >= 90% an alert and a
    pending collection are raised.
    """
    cfg = current_app.config
    candidates = (
        BinCompartment.query.join(SmartBin)
        .filter(SmartBin.location_id == location_id, BinCompartment.category == category)
        .all()
    )
    for comp in sorted(candidates, key=lambda c: (c.fill_percent, c.id)):
        result = db.session.execute(
            update(BinCompartment)
            .where(
                BinCompartment.id == comp.id,
                BinCompartment.current_load + volume <= BinCompartment.max_capacity,
            )
            .values(current_load=func.round(BinCompartment.current_load + volume, 3))
            .execution_options(synchronize_session=False)
        )
        if result.rowcount == 1:
            db.session.refresh(comp)  # pick up the value the database computed
            if comp.fill_percent >= cfg["ALERT_PERCENT"]:
                _raise_alert(comp)
            return comp
    return None


def _raise_alert(compartment):
    b = compartment.bin
    # Lock the bin row so concurrent requests cannot both create the alert / pending collection.
    # Locking reads also see rows committed by other requests after this transaction started.
    db.session.query(SmartBin).filter_by(id=b.id).with_for_update().one()
    exists = Alert.query.filter_by(compartment_id=compartment.id, resolved=False).with_for_update().first()
    if not exists:
        db.session.add(
            Alert(
                bin_id=b.id,
                compartment_id=compartment.id,
                message=(
                    f"{b.name} ({b.location.name}): {compartment.category} compartment "
                    f"is {compartment.fill_percent}% full (simulated)."
                ),
            )
        )
    if not CollectionRecord.query.filter_by(bin_id=b.id, status="pending").with_for_update().first():
        db.session.add(CollectionRecord(bin_id=b.id, status="pending"))

def reset_bin(bin_, admin_user):
    """Mark a bin as collected: store the collection, zero all compartments, resolve alerts."""
    now = datetime.utcnow()
    total = round(sum(c.current_load for c in bin_.compartments), 3)
    record = CollectionRecord.query.filter_by(bin_id=bin_.id, status="pending").first()
    if record is None:
        record = CollectionRecord(bin_id=bin_.id, requested_at=now)
        db.session.add(record)
    record.status = "completed"
    record.collected_at = now
    record.collected_by = admin_user.id
    record.volume_collected = total
    for c in bin_.compartments:
        c.current_load = 0.0
    for a in Alert.query.filter_by(bin_id=bin_.id, resolved=False).all():
        a.resolved = True
        a.resolved_at = now
    return record


def bin_status_counts(almost_full, alert):
    counts = {"Normal": 0, "Almost Full": 0, "Collection Required": 0}
    for b in SmartBin.query.all():
        counts[b.status(almost_full, alert)] += 1
    return counts
