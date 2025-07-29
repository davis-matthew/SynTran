import re
import subprocess

def verify(original_code_path, translated_code_path):
    translated = ""
    with open(translated_code_path, 'r') as file:
        translated = file.read()

    if len(matches) < 1:
        print("\tinvalid")
        return 'invalidgeneration', 'Code block not present in generated translation. Make sure you provide the code block and surround it with ```.'
    matches = re.findall(r'```(.*?)```', translated, re.DOTALL)

    path = ""
    verifier_response = subprocess.run(f"frama-c -kernel-warn-key typing:implicit-function-declaration=inactive,annot:missing-spec=inactive -wp -wp-precond-weakening -wp-no-callee-precond -wp-prover Alt-Ergo,Z3 -wp-print -wp-timeout 8 {path}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    verifier_response = verifier_response.stdout

    if 'An unknown error happened while running FRAMA-C WP' in verifier_response or "report as 'crash' at https://git.frama-c.com/pub/frama-c/issues" in verifier_response:
        return "verifier-crash", verifier_response
    elif '[wp] Proved goals' not in verifier_response:
        return "verifier-error", verifier_response
    else:
        false_goals = []
        timeout_goals = []
        for line in verifier_response.split("\n"):
            if line.startswith("[wp] Proved goals:"):
                match = re.search(r"(\d+)\s*/\s*(\d+)", line)
                if match:
                    goalsOK = int(match.group(1))
                    goalsTotal = int(match.group(2))
                    if goalsOK == goalsTotal:
                        return "success", "Successful Verification"
            if line.startswith("Prover ") and (" returns Timeout" in line or " returns Unknown" in line):
                self.hasTimeout = True
            if line.startswith("Prove: false."):
                self.hasProveFalse = True
            if not self.isError:
                goals = self._parseGoals()
                for goal in goals:
                    for line in goal.split("\n"):
                        if line.startswith("Prover ") and " returns Valid" in line:
                            self.passedGoals.append(goal)
                            break
                    else:
                        self.failedGoals.append(goal)
                if len(self.failedGoals) == 0:
                    return "success", "Successful Verification"