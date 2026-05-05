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

        # --- Area Santé count > Oracle count (remaining sub-case) ---
        # At this point: areaSanteDuplicateCount > oracleCount

        # Sub-case: how many lines did Pass 1 find?
        if oracleCount == 1:
            # 1 line found in Pass 1 and no "Reconciled" exists for dup key
            paymentLine.Status = "Reconciled"
            goto store_oracle_count_and_complete

        if oracleCount == 0:
            # 0 lines found in Pass 1 and no "Reconciled" exists for dup key
            # ═══ PASS 2 : Date = / Amount < ═══
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
                # Check if at least one line with same dup key is "Reconciled"
                if exists_line_with_same_duplicate_key_and_status(
                    ProcessingSheet,
                    paymentLine.DuplicateKey,
                    "Reconciled"
                ):
                    insert_missing_payment_lines_to_book_into_spreadsheet(paymentLine)
                    paymentLine.Treated = "To book"
                    goto store_oracle_count_and_complete

                # No Reconciled line found → go to Pass 3
                # ═══ PASS 3 : No Date / Amount = ═══
                go_back_to_previous_search_page()
                set_entered_amount_search_mode("equal", paymentLine.Amount)
                remove_oracle_field("Receipt date")
                click_search_button()
                oracleCount = count_lines_found_in_oracle()

                areaSanteDuplicateCount2 = count_lines_with_same_duplicate_key(
                    ProcessingSheet,
                    paymentLine.DuplicateKey
                )

                if oracleCount == areaSanteDuplicateCount2:
                    update_status_for_duplicate_key(
                        ProcessingSheet,
                        paymentLine.DuplicateKey,
                        "Reconciled"
                    )
                    goto store_oracle_count_and_complete

                if oracleCount > areaSanteDuplicateCount2:
                    update_status_for_duplicate_key(
                        ProcessingSheet,
                        paymentLine.DuplicateKey,
                        "Duplicated"
                    )
                    goto store_oracle_count_and_complete

                # Area Santé > Oracle in Pass 3
                # Check if "Reconciled" exists for same dup key
                if exists_line_with_same_duplicate_key_and_status(
                    ProcessingSheet,
                    paymentLine.DuplicateKey,
                    "Reconciled"
                ):
                    # ═══ PASS 4 : No Date / Amount < ═══
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

                    # Several found
                    paymentLine.Status = "To analyze"
                    goto finalize_current_line

                # No "Reconciled" in dup key in Pass 3
                if oracleCount == 1:
                    click_receipt_number_of_found_line()
                    paymentLine.OracleOriginalAmount = read_first_amount_from_history_tab()
                    paymentLine.OracleLastAmount = read_most_recent_amount_from_history_tab()
                    paymentLine.Status = "Reconciled"
                    goto store_oracle_count_and_complete

                if oracleCount == 0:
                    # ═══ PASS 4 : No Date / Amount < ═══
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

                    # Several found
                    paymentLine.Status = "To analyze"
                    goto finalize_current_line

                # Several found in Pass 3
                paymentLine.Status = "To analyze"
                goto finalize_current_line

            # Several found in Pass 2
            paymentLine.Status = "To analyze"
            goto finalize_current_line

        # Several lines found in Pass 1 sub-case
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
- The Oracle search logic is executed in up to four successive passes:
  - **Pass 1** — Client = / Paying Customer = / Date = / Amount =
  - **Pass 2** — Client = / Paying Customer = / Date = / Amount <
  - **Pass 3** — Client = / Paying Customer = / No Date / Amount =
  - **Pass 4** — Client = / Paying Customer = / No Date / Amount <
- Not all passes are always executed; the algorithm exits as soon as a definitive status is determined.
- The "Duplicate key" check (does a line with same key already have Status = "Reconciled"?) gates the transition between sub-branches:
  - In the "Area Santé > Oracle" sub-case of Pass 1: if YES → go to Pass 2; if NO → check 1-found/0-found sub-cases.
  - In the "Area Santé > Oracle" sub-case of Pass 3: if YES → go to Pass 4; if NO → check 1-found/0-found sub-cases.
  - In Pass 2 and Pass 4, when 0 lines are found: if a "Reconciled" dup key line exists → "To book"; otherwise → "To analyze".
- The four possible terminal statuses from the matching algorithm are: `Reconciled`, `Duplicated`, `Amended`, `To analyze`, `To book`.
- When a branch updates all rows sharing the same `Duplicate key`, the action applies to the whole duplicate group, not only to the current row.
- After each processed line, the workbook timing fields and the RPA UI counters are refreshed before the next loop iteration.

---

## Behavior Notes

- The algorithm must not rely on any user interaction after input files and parameters are provided.
- The algorithm must always follow the same deterministic path for the same inputs.
- The focus is on data validation, line-by-line processing, status assignment, and output generation.
