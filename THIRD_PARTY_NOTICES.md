# Third-party notices

## CMATH dataset

This repository includes a grade-five subset of the CMATH dataset in `backend/data/cmath_grade5_cc_by_4.jsonl`.

CMATH was created by Tianwen Wei, Jian Luan, Wei Liu, Shuang Dong and Bin Wang. The dataset is distributed under the [Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/).

Source: https://github.com/XiaoMi/cmath
Original file: https://github.com/XiaoMi/cmath/blob/main/datasets/cmath_dev.jsonl

Changes made by this project: records with `grade = 5` were extracted and reserialized as UTF-8 JSONL. At runtime, the project assigns curriculum-unit and teaching metadata with local heuristic rules. The original `input`, `golden`, `reasoning_step` and `num_digits` values are preserved.

The repository’s MIT license does not replace the CC BY 4.0 terms that apply to this dataset.
