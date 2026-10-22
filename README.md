# DPS970 – Activity 2

| Question | Where |
| --- | --- |
| **Q1** Monte Carlo tree search for Connect Four | code in `connect4/`, report in `REPORT_Q1.md`, data in `results/` |
| **Q2–Q4** Propositional logic | written answers in `ANSWERS_Q2_Q4.md`, code in `logic/` |

Python 3.8 or newer, **standard library only** (matplotlib is optional and only used to draw the report charts). The design follows the textbook's code: the `Game` interface and **Figure 5.11** (MONTE-CARLO-TREE-SEARCH) for Q1, and **TT-ENTAILS**, CNF conversion and **PL-RESOLUTION** from Chapter 7 for Q2–Q4.

## Project layout

```
Activity_02/
├── REPORT_Q1.md                 # Q1 report: experiments, data, analysis
├── ANSWERS_Q2_Q4.md             # Q2–Q4 written answers
├── connect4/
│   ├── game.py                  # Connect Four (6 x 7) with the textbook Game interface
│   ├── heuristic.py             # objective part of the utility (evaluation function)
│   ├── mcts.py                  # Figure 5.11: select / expand / simulate / back-propagate
│   ├── positions.py             # TEST DATA: test positions and their correct moves
│   ├── play.py                  # command line: get a move, or play against it
│   └── experiments.py           # runs all experiments, writes results/*.csv and charts
├── logic/
│   ├── logic.py                 # sentences, TT-ENTAILS, CNF, PL-RESOLUTION
│   └── answers.py               # prints the working for Q2–Q4
├── tests/
│   ├── test_connect4.py         # game rules, heuristic, MCTS behaviour
│   ├── test_logic.py            # parsing, validity, model counts, CNF, resolution
│   └── data/logic_cases.json    # TEST DATA: sentences with their expected class
├── results/                     # experiment output (CSV + charts) used in the report
└── .github/workflows/tests.yml  # GitHub Actions: tests + demos on every push
```

## Running the tests

From the `Activity_02` folder:

```bash
python3 -m unittest discover -s tests -t . -v
```

28 tests: Connect Four rules (wins in all four directions, full columns, turn order), the heuristic, the MCTS settings (cycles, expansion width, tree height, reproducibility with a seed, tactical positions, beating a random player), and the logic answers (validity, model counts, CNF, resolution).

**GitHub Actions:** push the folder to GitHub and `.github/workflows/tests.yml` runs the tests, a demo move, a quick experiment run and the Q2–Q4 working on Python 3.9 and 3.12.

## Q1 – using the move generator

```bash
python3 -m connect4.play                                            # empty board, default settings
python3 -m connect4.play --position double_threat --cycles 500 --k 3 --depth 4 --w 0.5 --seed 1
python3 -m connect4.play --rows "......." "......." "......." "......." "..OO..." "..XX..."
python3 -m connect4.play --human                                    # play against it (you are X)
```

| Option | Meaning | Default |
| --- | --- | --- |
| `--cycles` | number of select/expand/simulate/back-propagate rounds | 1000 |
| `--k` | expansion width x: children per node | 7 (all columns) |
| `--depth` | height of the tree; below it, only random playouts | 42 (no limit) |
| `--w` | weight of the objective (heuristic) part of the utility | 0.5 |
| `--c` | weight of the exploration part of the utility | 1.41 |
| `--order` | choose the x moves by `heuristic` or `random` | heuristic |
| `--seed` | fix the random numbers to repeat a run exactly | none |

Built-in positions: `empty`, `win_in_1`, `must_block`, `double_threat`.

**Reproducing the report data** (about 15–20 minutes):

```bash
python3 -m connect4.experiments              # writes results/*.csv and results/charts/*.png
python3 -m connect4.experiments --quick      # 15-second smoke test
python3 -m connect4.experiments --only A,E   # run only some experiments (A-F); progress is printed for every setting
```

## Q2–Q4 – printing the working

```bash
python3 -m logic.answers
```

Prints the truth tables for Q2 and Q4(a), the model counts for Q3, the CNF steps for Q4(b) and the resolution proof for Q4(c).
