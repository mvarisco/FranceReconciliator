# Deterministic Algorithm for AR Reconciliation

## Inputs

- `AreaSanteFile`: Excel file containing source payment lines.
- `OracleClientFile`: Excel file containing mapping from Social Security number to Oracle Client number.
- `Parameters`:
  - `period`
  - `maxLines`
  - `ignoreAmount`
  - `saveEach`
  - `sendMail`
  - `receivers`
  - `runHidden`

## Required columns in `AreaSanteFile`

- `Customer account`
- `Amount`
- `Receipt date`
- `Duplicate Key`
- `Social Security N°` or equivalent key for Oracle lookup

## Output

- `OutputWorkbook`: Excel workbook containing processed rows and a report sheet.

---

## Pseudocode

```
function main(AreaSanteFile, OracleClientFile, Parameters):
    AreaSanteData = load_excel(AreaSanteFile)
    OracleClientData = load_excel(OracleClientFile)

    validate_area_sante_structure(AreaSanteData)
    validate_oracle_client_structure(OracleClientData)

    OutputWorkbook = create_output_workbook(AreaSanteFile, Parameters)
    ProcessingSheet = prepare_processing_sheet(OutputWorkbook, AreaSanteData, OracleClientData)

    filteredLines = filter_lines(ProcessingSheet, Parameters)
    totalLines = count(filteredLines)
    treatedLines = 0

    for each line in filteredLines:
        if treatedLines >= Parameters.maxLines:
            break

        line.StartTime = now()

        if should_ignore_line(line, Parameters.ignoreAmount):
            line.Status = "Ignored"
            log_line(line, "INFO", "Ignored based on ignoreAmount")
            save_progress_if_needed(OutputWorkbook, Parameters, treatedLines)
            continue

        if not validate_line_fields(line):
            line.Status = "Data error"
            log_line(line, "ERROR", "Missing or invalid required field")
            save_progress_if_needed(OutputWorkbook, Parameters, treatedLines)
            continue

        oracleClientNumber = lookup_oracle_client_number(line, OracleClientData)
        line.OracleClientNumber = oracleClientNumber

        searchCriteria = build_search_criteria(line, oracleClientNumber)
        searchResult = query_oracle_receipts(searchCriteria)

        if searchResult.count == 0:
            line.Status = determine_no_line_status(line)
            line.Log = "No Oracle receipt found"
            save_progress_if_needed(OutputWorkbook, Parameters, treatedLines)
            continue

        if searchResult.count == 1:
            receipt = searchResult.receipts[0]
            line.OracleOriginalAmount = receipt.firstHistoryAmount
            line.OracleLastAmount = receipt.mostRecentHistoryAmount
            line.OracleDeltaAmount = compute_delta(line)
            line.Status = determine_single_line_status(line, receipt)
            log_line(line, "INFO", "Single receipt found")
            save_progress_if_needed(OutputWorkbook, Parameters, treatedLines)
            continue

        if searchResult.count > 1:
            line.CountOfOracleLines = searchResult.count
            line.CountOfAreaSanteLines = compute_duplicate_key_count(ProcessingSheet, line.DuplicateKey)
            line.CountOfExtraLinesInOracle = line.CountOfOracleLines - line.CountOfAreaSanteLines
            line.Status = determine_multi_line_status(line)
            log_line(line, "INFO", "Multiple Oracle receipts found")
            save_progress_if_needed(OutputWorkbook, Parameters, treatedLines)
            continue

        line.EndTime = now()
        line.ExecutionTime = line.EndTime - line.StartTime
        treatedLines += 1
        update_progress(OutputWorkbook, treatedLines, totalLines)

    refresh_execution_report(OutputWorkbook)
    save_workbook(OutputWorkbook)

    if all_lines_processed_successfully(filteredLines):
        if Parameters.sendMail:
            send_success_email(OutputWorkbook, Parameters.receivers)
        return "Success"
    else:
        if Parameters.sendMail:
            send_failure_email(OutputWorkbook, Parameters.receivers)
        return "Completed with issues"
```

---

## Supporting functions

### `validate_area_sante_structure(data)`

- check required headers exist
- check file has at least one data row
- if invalid, raise error

### `validate_oracle_client_structure(data)`

- check mapping key exists
- check at least one mapping row exists
- if invalid, raise error

### `prepare_processing_sheet(workbook, AreaSanteData, OracleClientData)`

- copy data into a working sheet
- add columns:
  - `Start time`
  - `End time`
  - `Status`
  - `Oracle Client N°`
  - `Oracle Original Amount`
  - `Oracle Last Amount`
  - `Oracle Delta Amount`
  - `Count of lines in Area Santé`
  - `Count of Extra lines in Oracle`
  - `Count of Reversed Extra lines`
  - `Date`, `Time`, `Level`, `Log`
- add formulas or placeholders for columns
- return the working sheet reference

### `filter_lines(sheet, Parameters)`

- apply period filter
- apply ignore amount threshold filter
- limit to `maxLines`
- return ordered list of line objects

### `should_ignore_line(line, ignoreAmount)`

- return true if line.Amount >= ignoreAmount

### `validate_line_fields(line)`

- return false if any required field is missing or invalid

### `lookup_oracle_client_number(line, OracleClientData)`

- return Oracle Client number using Social Security number lookup
- if lookup fails, return null or error state

### `build_search_criteria(line, oracleClientNumber)`

- return object with:
  - `Client`
  - `Paying Customer`
  - `Date`
  - `Amount`

### `query_oracle_receipts(criteria)`

- execute deterministic lookup in Oracle
- return searchResults with count and receipt details

### `determine_no_line_status(line)`

- return `Ignored` or `To analyze` depending on business rule

### `determine_single_line_status(line, receipt)`

- if receipt amounts reconcile: return `Reconciled`
- if duplicate indicators exist: return `Duplicated`
- if adjustment required: return `Amended`

### `determine_multi_line_status(line)`

- compare Oracle line count with `Count of lines in Area Santé`
- if equal: return `Reconciled`
- if Oracle count greater: return `Duplicated` or `Amended`
- if Area Santé count greater: return `To analyze`

### `compute_delta(line)`

- return `line.OracleLastAmount - line.OracleOriginalAmount`

### `log_line(line, level, message)`

- write a log entry to the line record

### `update_progress(workbook, treatedLines, totalLines)`

- compute progress percentage
- update remaining time estimate

### `refresh_execution_report(workbook)`

- rebuild pivot and summary information

### `save_progress_if_needed(workbook, Parameters, treatedLines)`

- save workbook after every `Parameters.saveEach` processed lines

---

## Behavior Notes

- The algorithm must not rely on any user interaction after input files and parameters are provided.
- The algorithm must always follow the same deterministic path for the same inputs.
- The focus is on data validation, line-by-line processing, status assignment, and output generation.
