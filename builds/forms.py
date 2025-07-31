from django import forms
from django.core.exceptions import ValidationError
import json

from .models import Build, BuildLog
from admin_utils.json_widget import JSONEditorWidget


class BuildForm(forms.ModelForm):
    """Form for Build model with enhanced validation"""

    # Build configuration
    build_config = forms.JSONField(
        required=False,
        widget=JSONEditorWidget(attrs={
            'style': 'height: 300px;',
            'placeholder': json.dumps({
                'flutter_version': '3.16.0',
                'build_mode': 'release',
                'target_platform': 'android-arm64',
                'enable_obfuscation': False,
                'split_per_abi': True
            }, indent=2)
        })
    )

    # Environment variables
    environment_variables = forms.JSONField(
        required=False,
        widget=JSONEditorWidget(attrs={
            'style': 'height: 200px;',
            'placeholder': json.dumps({
                'FLUTTER_BUILD_MODE': 'release',
                'ANDROID_SDK_ROOT': '/path/to/android-sdk'
            }, indent=2)
        }),
        help_text='Environment variables to set during build process'
    )

    class Meta:
        model = Build
        fields = '__all__'
        widgets = {
            'build_log': forms.Textarea(attrs={
                'rows': 10,
                'readonly': True,
                'class': 'build-log-textarea'
            }),
            'error_message': forms.Textarea(attrs={
                'rows': 3,
                'readonly': True,
                'class': 'error-message-textarea'
            }),
            'error_stacktrace': forms.Textarea(attrs={
                'rows': 8,
                'readonly': True,
                'class': 'stacktrace-textarea'
            }),
            'version': forms.TextInput(attrs={
                'placeholder': '1.0.0+1',
                'pattern': r'^\d+\.\d+\.\d+\+\d+$'
            }),
            'commit_hash': forms.TextInput(attrs={
                'placeholder': 'git commit hash (optional)',
                'maxlength': 40
            })
        }
        help_texts = {
            'platform': 'Target platform for the build',
            'version': 'Version in format: major.minor.patch+build (e.g., 1.0.0+1)',
            'commit_hash': 'Git commit hash for tracking source code version'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make certain fields read-only for existing builds
        if self.instance and self.instance.pk:
            readonly_fields = ['project', 'build_number', 'status', 'apk_file']
            for field in readonly_fields:
                if field in self.fields:
                    self.fields[field].disabled = True

        # Set initial status for new builds
        if not self.instance.pk:
            self.fields['status'].initial = 'pending'

    def clean_version(self):
        version = self.cleaned_data.get('version')

        if version:
            # Validate version format
            import re
            pattern = r'^\d+\.\d+\.\d+\+\d+$'
            if not re.match(pattern, version):
                raise ValidationError(
                    'Version must be in format: major.minor.patch+build (e.g., 1.0.0+1)'
                )

        return version

    def clean_build_config(self):
        config = self.cleaned_data.get('build_config')

        if config:
            # Validate required fields
            if 'flutter_version' not in config:
                config['flutter_version'] = '3.16.0'

            if 'build_mode' not in config:
                config['build_mode'] = 'release'

            # Validate build mode
            valid_modes = ['debug', 'profile', 'release']
            if config['build_mode'] not in valid_modes:
                raise ValidationError(
                    f"Invalid build mode. Must be one of: {', '.join(valid_modes)}"
                )

            # Validate platform-specific settings
            if 'target_platform' in config:
                valid_platforms = [
                    'android-arm', 'android-arm64', 'android-x64',
                    'ios', 'ios-simulator'
                ]
                if config['target_platform'] not in valid_platforms:
                    raise ValidationError(
                        f"Invalid target platform. Must be one of: {', '.join(valid_platforms)}"
                    )

        return config

    def clean_commit_hash(self):
        commit_hash = self.cleaned_data.get('commit_hash')

        if commit_hash:
            # Validate Git commit hash format (40 character hex)
            import re
            if not re.match(r'^[a-fA-F0-9]{40}$', commit_hash):
                # Also allow short hashes (7+ characters)
                if not re.match(r'^[a-fA-F0-9]{7,40}$', commit_hash):
                    raise ValidationError(
                        'Invalid Git commit hash. Must be 7-40 hexadecimal characters.'
                    )

        return commit_hash

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        apk_file = cleaned_data.get('apk_file')

        # Validate that successful builds have APK files
        if status == 'success' and not apk_file and self.instance.pk:
            self.add_error('status', 'Successful builds must have an APK file.')

        # Validate that only completed builds have completion time
        if status in ['pending', 'building'] and self.instance.completed_at:
            self.instance.completed_at = None

        return cleaned_data


class BuildLogForm(forms.ModelForm):
    """Form for BuildLog entries"""

    class Meta:
        model = BuildLog
        fields = '__all__'
        widgets = {
            'message': forms.Textarea(attrs={
                'rows': 3,
                'class': 'log-message-textarea'
            }),
            'extra_data': JSONEditorWidget(attrs={
                'style': 'height: 200px;'
            })
        }

    def clean_level(self):
        level = self.cleaned_data.get('level')

        valid_levels = ['debug', 'info', 'warning', 'error', 'critical']
        if level not in valid_levels:
            raise ValidationError(
                f"Invalid log level. Must be one of: {', '.join(valid_levels)}"
            )

        return level


class BuildFilterForm(forms.Form):
    """Form for filtering builds in admin"""

    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('pending', 'Pending'),
        ('building', 'Building'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled')
    ]

    PLATFORM_CHOICES = [
        ('', 'All Platforms'),
        ('android', 'Android'),
        ('ios', 'iOS')
    ]

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    platform = forms.ChoiceField(
        choices=PLATFORM_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by project name or version...',
            'class': 'form-control'
        })
    )