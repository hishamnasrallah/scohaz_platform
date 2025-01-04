from django import forms


class TranslationForm(forms.Form):
    """Form to edit translation keys and values."""
    key = forms.CharField(max_length=255)
    value = forms.CharField(widget=forms.Textarea)

    def clean_key(self):
        key = self.cleaned_data.get('key')
        # Replace spaces with underscores
        key = key.replace(" ", "_")
        return key
