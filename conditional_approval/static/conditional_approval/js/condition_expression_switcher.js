(function($) {
    // Function to switch condition_expression field based on 'type' field value
    function switchConditionExpressionField(typeField) {
        // Log the entire typeField to inspect it
        console.log("typeField:", typeField);

        // Get the value of the type field (AUTO_ACTION or CONDITION)
        var typeFieldValue = typeField.val();

        // Log the type field value to make sure it's being accessed correctly
        console.log("typeFieldValue:", typeFieldValue);

        // Extract the row index from the name attribute
        var rowIndex = typeField.attr('name').match(/\d+/);  // Match the digits in the field name

        // If no index found, log an error and return
        if (!rowIndex) {
            console.error("Row index extraction failed.");
            return; // Exit early if we can't extract row index
        }

        // Get the row index (first match)
        rowIndex = rowIndex[0];
        console.log("Row index:", rowIndex);

        // Find the condition_expression field based on the row index
        var conditionExpressionField = $('#id_approvalstepcondition_set-' + rowIndex + '-condition_expression'); // Input field (text field)
        var conditionExpressionDropdown = $('#id_approvalstepcondition_set-' + rowIndex + '-condition_expression'); // Dropdown (select field)

        // Ensure that we have the correct field
        console.log("conditionExpressionField:", conditionExpressionField);
        console.log("conditionExpressionDropdown:", conditionExpressionDropdown);

        if (typeFieldValue === '1') {  // Value for 'Condition'
            // If type is CONDITION, show the text field (condition_expression)
            conditionExpressionField.prop('disabled', false);  // Enable the text field
            conditionExpressionField.show();  // Show the text input field
            conditionExpressionDropdown.prop('disabled', true); // Disable the dropdown
            conditionExpressionDropdown.hide(); // Hide the dropdown
        } else if (typeFieldValue === '2') {  // Value for 'Automatic Action'
            // If type is AUTO_ACTION, switch to dropdown (select)
            conditionExpressionField.prop('disabled', true);  // Disable the text field
            conditionExpressionDropdown.prop('disabled', false); // Enable the dropdown
            conditionExpressionField.hide();  // Hide the text input field
            conditionExpressionDropdown.show(); // Show the dropdown
        }
    }

    // Run when the page loads
    $(document).ready(function() {
        // Apply to each inline form row
        $('.inline-related').each(function() {
            var typeField = $(this).find('select[name$="-type"]'); // Find the 'type' field in this row
            switchConditionExpressionField(typeField);  // Switch the condition_expression field initially
        });

        // Listen for changes to the 'type' field and dynamically switch the field
        $(document).on('change', 'select[name$="-type"]', function() {
            switchConditionExpressionField($(this));  // Re-run the switch function when 'type' changes
        });
    });
})(django.jQuery);
