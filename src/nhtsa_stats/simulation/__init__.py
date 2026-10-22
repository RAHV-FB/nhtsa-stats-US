"""Policy simulation tooling (RQ10): evidence ledger, intervention engine and cost model.

* ``engine``   -- four-layer intervention simulator (A empirical baseline, B mechanisms,
  C user assumptions, D hypothetical outcomes);
* ``costs``    -- programme cost model, cost-effectiveness and break-even analysis;
* ``evidence`` -- evidence ledger linking empirical findings to interventions.

Nothing in this package estimates the effect of an intervention from the data: the database
contains no enforcement, camera, testing-programme or cost information.  Every simulated
quantity is *hypothetical*, conditional on user-supplied assumptions (see
``docs/policy_assumptions.md``).
"""
