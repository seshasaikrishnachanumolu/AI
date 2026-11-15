"""Virtual smart bin logic. Fullness is SIMULATED from configured capacity and
estimated waste volume; it is not measured by sensors."""
from datetime import datetime

from flask import current_app

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


def find_compartment(location_id, category, volume):
    """Pick the compartment for `category` with the lowest fill among bins at the
    location that still have room for `volume`. Returns None if all are full."""
    candidates = (
        BinCompartment.query.join(SmartBin)
        .filter(SmartBin.location_id == location_id, BinCompartment.category == category)
        .all()
    )
    with_room = [c for c in candidates if c.current_load + volume <= c.max_capacity]
    if not with_room:
        return None
    return min(with_room, key=lambda c: c.fill_percent)


def add_waste(compartment, volume):
    """Increase simulated load; raise an alert and a pending collection at >= 90%."""
    cfg = current_app.config
    compartment.current_load = round(compartment.current_load + volume, 3)
    db.session.flush()
    if compartment.fill_percent >= cfg["ALERT_PERCENT"]:
        _raise_alert(compartment)


def _raise_alert(compartment):
    b = compartment.bin
    exists = Alert.query.filter_by(
        compartment_id=compartment.id, resolved=False
    ).first()
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
    if not CollectionRecord.query.filter_by(bin_id=b.id, status="pending").first():
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
