"""Observed deaths by overlapping target segment and the evidence ledger (RQ9, RQ10).

* ``baseline`` -- FARS deaths and CRSS crashes by overlapping segment (speeding, alcohol, drugs,
  unrestrained occupants), and a search of the column inventory for enforcement or cost fields;
* ``evidence`` -- evidence ledger linking measured findings to candidate interventions; the CLI
  module ``policy`` runs the ledger and then ``baseline.run``.

Nothing in this package estimates the effect of an intervention: the database contains no
enforcement, camera, testing-programme or cost information.
"""
