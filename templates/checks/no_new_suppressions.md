# Fix the cause instead of adding a suppression

The suppression baseline may only shrink. Fix the reported lint or type error in the source, then remove the obsolete baseline entry. Do not add a tolerated error to make the check pass. If an exception is truly required, explain it to the user and obtain approval before changing the baseline.
