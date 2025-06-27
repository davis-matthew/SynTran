frama-c -kernel-warn-key typing:implicit-function-declaration=inactive,annot:missing-spec=inactive -wp -wp-precond-weakening -wp-no-callee-precond -wp-prover Alt-Ergo,Z3 -wp-print -wp-timeout 8 content

response

if 'An unknown error happened while running FRAMA-C WP.' == response or "report as 'crash' at https://git.frama-c.com/pub/frama-c/issues" in response:
    crashed.
elif '[wp] Proved goals' not in response:
    error.
else:
    