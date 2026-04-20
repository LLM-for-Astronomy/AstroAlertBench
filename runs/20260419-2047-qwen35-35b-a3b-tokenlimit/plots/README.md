# Plots for this run

## `per_class_accuracy.png`

Bar chart of accuracy within each of the five ground-truth classes. Horizontal dashed line at 20 % marks random-guess baseline. Overlays the per-class sample count as grey text.


![per_class_accuracy.png](./per_class_accuracy.png)

## `five_class_confusion.png`

End-to-end 5-class confusion matrix (SN / AGN / VS / asteroid / bogus / N-A). Rows are gold labels, columns are predicted 5-class labels derived from the staged Part-C output. Unparseable rows land in N-A. Values are raw counts.


![five_class_confusion.png](./five_class_confusion.png)

## `stage3_confusion.png`

Stage-3 subclass confusion restricted to rows that reached Stage 3. Rows are gold astrophysical classes (SN / VS / AGN), columns are the model's Stage-3 prediction (supernova / variable_star / AGN / N-A).


![stage3_confusion.png](./stage3_confusion.png)

## `token_distribution.png`

Histogram of n_output_tokens per row (full generation including thinking). Red dashed line at the max_tokens budget shows how close the model came to the token ceiling. Truncated runs are rows at or near that line.


![token_distribution.png](./token_distribution.png)

## `error_breakdown.png`

Counts of each format-error category (mutually exclusive per row). Includes 'ok' for cleanly parsed rows. Useful for spotting runs dominated by truncation vs malformed JSON vs schema issues.


![error_breakdown.png](./error_breakdown.png)

## `calibration.png`

Scatter of self-reported MSRS (mean of three Part-B self-scores) vs binary correctness of the final 5-class prediction. Correct = 1, wrong = 0. If the model is well calibrated, high-confidence predictions should be correct. Generated only when >= 5 linked records exist.


![calibration.png](./calibration.png)
