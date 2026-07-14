# Prompt Optimization Reminder

For each question, select one answer and briefly explain why.

## 1. Final evaluation

Which data should determine the final reported performance?

- A. The training set used to build demonstrations
- B. The validation data used during optimizer selection
- C. A held-out test set not used during optimization

## 2. Optimizer selection

An optimizer tries several candidate programs. Where should it compare them?

- A. On validation data
- B. On the final test data
- C. Only on training data

## 3. Reproducibility

What is most important to record when sampling a small dataset?

- A. Only the final accuracy
- B. Split sizes, sampling method, and random seed
- C. The time of day the script ran

## 4. Data leakage

Which action creates the clearest test leakage?

- A. Reading test labels to choose the best prompt
- B. Defining the output label names from the task schema
- C. Reporting per-class test accuracy after optimization is finished

## 5. Few-shot quality

How should a few-shot program be preferred over a baseline?

- A. It contains more examples
- B. Its prompt looks more detailed
- C. It performs better on appropriate held-out data
