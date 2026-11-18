ROLES = ('admin', 'estimator', 'viewer')
ESTIMATE_STATES = ('draft', 'calculating', 'estimated', 'requested', 'committed', 'failed')
STEELS = ('P20', 'H13', 'S136')

EXECUTION_STATES = ('running', 'completed', 'settled')
REVIEW_STATES = ('draft', 'signed')

MAINTENANCE_STATES=('planned','approved','completed')
RESIN_STATES=('available','quarantine')
MATERIAL_STATES=('issued','returned')
DELIVERY_STATES=('dispatched','received','accepted','rectification','closed')

SWITCH_STATES=('pending','rejected','eligible','switched')
# Minimum comparable signed samples: overall pool and per candidate machine.
SWITCH_MIN_TOTAL=5
SWITCH_MIN_PER_MACHINE=2
# 90% two-sided interval on predicted machine hours.
SWITCH_INTERVAL_ALPHA=0.10
# Normalised Euclidean radius inside which a signed trial counts as comparable.
SWITCH_COMPARABLE_RADIUS=2.0
