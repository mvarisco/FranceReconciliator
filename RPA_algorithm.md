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

The following pseudocode mirrors the flowchart logic from the node `For each payment lines` onward.

```
function process_payment_lines(ProcessingSheet, Parameters):
    totalLines = count_all_payment_lines(ProcessingSheet)
    treatedLines = 0
    runStartTime = now()

    for each paymentLine in ProcessingSheet:
        paymentLine.StartTime = now()

        if not columns_are_filled_and_formatted(
            paymentLine,
            ["Customer account", "Amount", "Receipt date"]
        ):
            paymentLine.Status = "Data error"
            goto finalize_current_line

        if paymentLine.Amount < Parameters.ignoreAmount:
            paymentLine.Status = "Ignored"
            goto finalize_current_line

        if paymentLine.Status is not empty:
            goto finalize_current_line

        fill_oracle_field("Customer Account Number", paymentLine.CustomerAccount)
        fill_oracle_field("Paying Customer", "00500133712631")
        fill_oracle_field("Receipt date", convert_date_for_oracle(paymentLine.ReceiptDate))
        fill_oracle_field("Entered Amount", paymentLine.Amount)
        click_search_button()

        oracleCount = count_lines_found_in_oracle()
        areaSanteDuplicateCount = count_lines_with_same_duplicate_key(
            ProcessingSheet,
            paymentLine.DuplicateKey
        )

        if oracleCount == areaSanteDuplicateCount:
            update_status_for_duplicate_key(
                ProcessingSheet,
                paymentLine.DuplicateKey,
                "Reconciled"
            )
            goto store_oracle_count_and_complete

        if oracleCount > areaSanteDuplicateCount:
            update_status_for_duplicate_key(
                ProcessingSheet,
                paymentLine.DuplicateKey,
                "Duplicated"
            )
            goto store_oracle_count_and_complete

        if exists_line_with_same_duplicate_key_and_status(
            ProcessingSheet,
            paymentLine.DuplicateKey,
            "Reconciled"
        ):
            go_back_to_previous_search_page()
            set_entered_amount_search_mode("less_than", paymentLine.Amount)
            click_search_button()
            oracleCount = count_lines_found_in_oracle()

            if oracleCount == 1:
                click_receipt_number_of_found_line()
                paymentLine.OracleOriginalAmount = read_first_amount_from_history_tab()
                paymentLine.OracleLastAmount = read_most_recent_amount_from_history_tab()
                paymentLine.Status = "Amended"
                goto store_oracle_count_and_complete

            if oracleCount == 0:
                insert_missing_payment_lines_to_book_into_spreadsheet(paymentLine)
                paymentLine.Treated = "To book"
                goto store_oracle_count_and_complete

            paymentLine.Status = "To analyze"
            goto finalize_current_line

        if oracleCount == 1:
            paymentLine.Status = "Reconciled"
            goto store_oracle_count_and_complete

        if oracleCount == 0:
            go_back_to_previous_search_page()
            set_entered_amount_search_mode("equal", paymentLine.Amount)
            remove_oracle_field("Receipt date")
            click_search_button()
            oracleCount = count_lines_found_in_oracle()

            if oracleCount == areaSanteDuplicateCount:
                update_status_for_duplicate_key(
                    ProcessingSheet,
                    paymentLine.DuplicateKey,
                    "Reconciled"
                )
                goto store_oracle_count_and_complete

            if oracleCount > areaSanteDuplicateCount:
                update_status_for_duplicate_key(
                    ProcessingSheet,
                    paymentLine.DuplicateKey,
                    "Duplicated"
                )
                goto store_oracle_count_and_complete

            if oracleCount == 1:
                click_receipt_number_of_found_line()
                paymentLine.OracleOriginalAmount = read_first_amount_from_history_tab()
                paymentLine.OracleLastAmount = read_most_recent_amount_from_history_tab()
                paymentLine.Status = "Reconciled"
                goto store_oracle_count_and_complete

            if oracleCount == 0:
                go_back_to_previous_search_page()
                set_entered_amount_search_mode("less_than", paymentLine.Amount)
                click_search_button()
                oracleCount = count_lines_found_in_oracle()

                if oracleCount == 1:
                    click_receipt_number_of_found_line()
                    paymentLine.OracleOriginalAmount = read_first_amount_from_history_tab()
                    paymentLine.OracleLastAmount = read_most_recent_amount_from_history_tab()
                    paymentLine.Status = "Amended"
                    goto store_oracle_count_and_complete

                if oracleCount == 0:
                    if exists_line_with_same_duplicate_key_and_status(
                        ProcessingSheet,
                        paymentLine.DuplicateKey,
                        "Reconciled"
                    ):
                        insert_missing_payment_lines_to_book_into_spreadsheet(paymentLine)
                        paymentLine.Treated = "To book"
                        goto store_oracle_count_and_complete

                    paymentLine.Status = "To analyze"
                    goto finalize_current_line

                paymentLine.Status = "To analyze"
                goto finalize_current_line

            paymentLine.Status = "To analyze"
            goto finalize_current_line

        paymentLine.Status = "To analyze"
        goto finalize_current_line

        label store_oracle_count_and_complete:
            paymentLine.CountOfOracleLines = oracleCount

            if oracleCount > 0:
                paymentLine.CountOfReversedExtraLines = count_reversed_lines_in_oracle()
                paymentLine.ReceiptDateInOracle = read_receipt_date_from_oracle()
                paymentLine.BankAccount = read_remittance_bank_account_from_oracle()

        label finalize_current_line:
            paymentLine.EndTime = now()
            treatedLines = treatedLines + 1
            paymentLine.LastExecutionTime = paymentLine.EndTime - paymentLine.StartTime
            executionTime = now() - runStartTime
            remainingTime = paymentLine.LastExecutionTime * (totalLines - treatedLines)
            progressPercent = (treatedLines / totalLines) * 100

            update_ui_execution_time(executionTime)
            update_ui_remaining_time(remainingTime)
            update_ui_treated_lines_counter(treatedLines)
            update_ui_progress(progressPercent)

            if treatedLines % Parameters.saveEach == 0:
                save_excel_file()

            if treatedLines == totalLines:
                break

    save_excel_file()
    build_pivot_report_sheet("Execution report")
    send_success_email_with_attachment()
    display_success_popup()
```

---

## Flow Notes

- `Data error` is assigned when at least one of `Customer account`, `Amount`, or `Receipt date` is missing or not correctly formatted.
- `Ignored` is assigned when the amount is below the `ignoreAmount` parameter.
- A line with an already filled `Status` is skipped because it is considered already treated.
- The Oracle search logic is executed in four successive modes:
  - exact date and exact amount
  - exact date and amount less than the Excel amount
  - no date and exact amount
  - no date and amount less than the Excel amount
- `Reconciled`, `Duplicated`, `Amended`, `To analyze`, and `To book` are assigned according to the branch reached in the flowchart.
- When a branch updates all rows sharing the same `Duplicate key`, the action applies to the whole duplicate group, not only to the current row.
- After each processed line, the workbook timing fields and the RPA UI counters are refreshed before the next loop iteration.

---

## Behavior Notes

- The algorithm must not rely on any user interaction after input files and parameters are provided.
- The algorithm must always follow the same deterministic path for the same inputs.
- The focus is on data validation, line-by-line processing, status assignment, and output generation.
