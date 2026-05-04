# RPA Specification for AR Reconciliation Process

## Purpose

This document defines a deterministic algorithm that starts from the input file `Area Santé` and performs the reconciliation process step by step. All actions are written as explicit operational steps.

## Input

- Primary input: `Area Santé` Excel file.
- Secondary input: `Oracle Client` Excel file used for mapping Social Security number to Oracle Client number.
- User parameters:
  - period
  - max lines
  - ignore amount
  - save each
  - send mail
  - receivers
  - run hidden

## Precondition

The algorithm assumes the `Area Santé` file contains a valid table with the required columns. Required columns include at least:

- `Customer account`
- `Amount`
- `Receipt date`
- `Duplicate Key`
- `Social Security N°` or equivalent identifier used for Oracle Client mapping

If the file does not contain required columns or contains an invalid layout, the process must stop immediately and report the error.

## Deterministic Algorithm Steps

### 1. Load and validate input

1. Open the `Area Santé` Excel file.
2. Verify the file has the expected sheet structure.
3. Verify header names and column order for required columns.
4. Verify the file contains at least one data row.
5. If the file is invalid, stop the algorithm and report:
   - missing required columns
   - invalid column order
   - incorrect row count
   - wrong file format

### 2. Open auxiliary input data

6. Open the `Oracle Client` Excel file.
7. Verify the `Oracle Client` file has the mapping information needed to convert Social Security number into Oracle Client number.
8. If the Oracle Client file is invalid, stop and report the error.

### 3. Create working output workbook

9. Create a new Excel output file in SharePoint using the naming convention:
   - `RPA_AR_booking_DD-MM-AAAA_HH-MM`
10. In the output workbook, duplicate the original `Area Santé` sheet and keep the name `Area Santé`.
11. Duplicate the `Area Santé` sheet again as the `RPA` sheet if required for processing.
12. Duplicate the `Area Santé` sheet as the `Execution report` sheet at the end of the run.
13. Rename the duplicated copies as appropriate:
   - `Area Santé`
   - `RPA`
   - `Execution report`

### 4. Prepare the Excel processing sheet

14. Add the following columns to the working sheet if they do not already exist:
    - `Start time`
    - `End time`
    - `Status` (text)
    - `Oracle Client N°` (formula using VLOOKUP from Oracle Client file)
    - `Oracle Original Amount` (empty numeric)
    - `Oracle Last Amount` (empty numeric)
    - `Oracle Delta Amount` (formula: `Oracle Last Amount - Oracle Original Amount`)
    - `Count of lines in Area Santé` (formula counting rows with same `Duplicate Key`)
    - `Count of Extra lines in Oracle` (formula: `Count of Lines in Oracle - Count of lines in Area Santé`)
    - `Count of Reversed Extra lines` (numeric)
    - `Status` values: `Duplicated`, `To analyze`, `Amended`, `Reconciled`, `To book`, `Data error`, `Ignored`
    - `Date`, `Time`, `Level`, `Log`
15. Add filters to all columns and freeze the top row.
16. Add a pivot table report in the `Execution report` sheet.

### 5. Filter lines before processing

17. Apply the user selection filters to the `Area Santé` sheet:
    - period filter
    - maximum number of lines (`max lines`)
    - ignore amount threshold
18. Create a working set of lines to process after filtering.
19. Update the workbook with a line count and set the initial counter values:
    - total lines to process
    - treated lines = 0
    - remaining time = unknown until first line processed

### 6. Process each payment line sequentially

For each line in the filtered working set, perform the following deterministic steps:

#### 6.1 Start line processing

20. Record current time in the `Start time` column for the current line.
21. Evaluate the line against the `ignore amount` parameter:
    - if the line `Amount` is greater than or equal to the `ignore amount` parameter, set `Status` = `Ignored` and skip to the next line.

22. Validate required field values for the current line:
    - `Customer account`
    - `Amount`
    - `Receipt date`
    - Oracle Client mapping key (Social Security N° or equivalent)
23. If any required field is missing or invalid, set `Status` = `Data error` and skip to the next line.

#### 6.2 Determine search values

24. Compute the search criteria for Oracle:
    - `Customer Account Number` from the current line
    - `Entered Amount` from the current line
    - `Receipt date` from the current line, formatted to Oracle date format
25. Resolve the Oracle Client number from the `Oracle Client` lookup table using the line’s Social Security number.

#### 6.3 Perform Oracle Fusion search

26. Open Oracle Fusion production.
27. Login to Oracle Fusion.
28. Navigate to the "Manage receipts" page.
29. In the Oracle UI, enter the search fields:
    - Client = Oracle Client number
    - Paying Customer = Customer account number
    - Date = formatted receipt date or no date if not available
    - Amount = entered amount
30. Click the Search button.

#### 6.4 Handle search results

31. Count the number of matching receipt lines returned by Oracle:
    - `No lines found`
    - `One line found`
    - `Multiple lines found`

32. If no lines are found:
    - set `Status` = `To analyze` or `Ignored` depending on business rule
    - log the condition in the `Log` column
    - update the corresponding counters and continue to the next line

33. If one line is found:
    - click the receipt number
    - inspect the `History` tab
    - identify the first amount in history
    - identify the most recent amount in history
    - write these values into `Oracle Original Amount` and `Oracle Last Amount`
    - compute `Oracle Delta Amount`
    - evaluate whether reconciliation succeeded:
      - if the amounts match and line counts align, set `Status` = `Reconciled`
      - if duplicates are found, set `Status` = `Duplicated`
      - if an adjustment is needed, set `Status` = `Amended`

34. If multiple lines are found:
    - count lines found in Oracle
    - compare with the `Count of lines in Area Santé` for the current `Duplicate Key`
    - set `Status` based on comparison:
      - if Oracle count equals Area Santé count, reconcile by matching groups
      - if Oracle count is greater, set `Status` = `Duplicated` or `Amended`
      - if Area Santé count is greater, set `Status` = `To analyze`
    - update `Count of Extra lines in Oracle` and `Count of Reversed Extra lines`

#### 6.5 Finalize the line

35. Record current time in the `End time` column.
36. Compute line execution time: `End time - Start time`.
37. Update progress values:
    - increment `treated lines`
    - update remaining time estimate
    - update progress percentage: `(treated lines / total lines) * 100`
38. Write a log entry in `Date`, `Time`, `Level`, `Log` describing the outcome.

### 7. Periodic save and exit conditions

39. After every `save each` number of lines, save the Excel workbook.
40. If the current line count reaches `max lines`, stop processing further lines.
41. If a critical error occurs, save the file, send a failure notification, and stop.

### 8. Final report and output

42. After processing all lines, build or refresh the pivot report in the `Execution report` sheet.
43. Save the Excel file.
44. If the run completes successfully, send a success email with the output file attached.
45. Display a success pop-up.

## Output File Structure

The output workbook must contain:

- `Area Santé` sheet with the processed data and status columns.
- `RPA` processing sheet, if used for intermediate conversion.
- `Execution report` sheet with the summary pivot report.

## Exception handling

- Any validation error stops the algorithm before processing the main loop.
- Any line-specific data error marks that line as `Data error` and continues.
- Any unrecoverable error stops the algorithm and triggers failure notification.

## Deterministic requirements

- The algorithm must always follow the same sequence of validation, sheet creation, column preparation, line processing, and reporting.
- The process must not depend on manual intervention once the required files and parameters are provided.
- All steps must be reproducible for the same input file and parameter values.
