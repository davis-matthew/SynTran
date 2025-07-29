import os
import sys
from collections import defaultdict

def gather_results(base_path):
    summary = defaultdict(lambda: {'solved': (0,[]), 'unsolved': (0,[]), 'skipped': (0,[])})

    for llm_name in os.listdir(base_path):
        problems_path = os.path.join(base_path, llm_name)
        if not os.path.isdir(problems_path):
            continue

        for problem in os.listdir(problems_path):
            problem_path = os.path.join(problems_path, problem)
            if not os.path.isdir(problem_path):
                continue

            files = os.listdir(problem_path)
            if 'solution' in files:
                count, items = summary[llm_name]['solved']
                items.append(problem)
                summary[llm_name]['solved'] = (count+1, items)
            elif 'terminated' in files:
                count, items = summary[llm_name]['skipped']
                items.append(problem)
                summary[llm_name]['skipped'] = (count+1, items)
            else:
                count, items = summary[llm_name]['unsolved']
                items.append(problem)
                summary[llm_name]['unsolved'] = (count+1, items)

    return summary

def create_latex_table(summary):
    latex = r"""\begin{tabular}{|l|c|c|c|}
\hline
LLM & Solved & Total & Skipped \\
\hline
"""
    for llm, counts in summary.items():
        solved = counts['solved'][0]
        total = solved + counts['unsolved'][0]
        skipped = counts['skipped'][0]
        latex += f"{llm} & {solved} & {total} & {skipped} \\\\\n"

    latex += r"\hline" + "\n\\end{tabular}"
    return latex

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <path_to_base_directory>")
        sys.exit(1)

    base_path = sys.argv[1]
    results = gather_results(base_path)
    latex_table = create_latex_table(results)
    print("\nLaTeX Table:\n")
    print(latex_table)

    print("\n\n")
    print(dict(results))