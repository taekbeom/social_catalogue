from datetime import datetime

from django import forms
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_date

from .models import News, Entry, AuthorInf


class NewsCreationForm(forms.ModelForm):

    class Meta:
        model = News
        fields = ["title", "message"]

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_title(self):
        title = self.cleaned_data.get('title').strip()
        if not title:
            raise ValidationError("Please enter title.")
        return title

    def clean_message(self):
        message = self.cleaned_data.get('message').strip()
        if not message:
            raise ValidationError("Please enter message.")
        return message


class EntryCreationForm(forms.ModelForm):

    date_selection = forms.CharField(required=False)

    class Meta:
        model = Entry
        fields = ["title", "alt_title", "add_date", "fin_date", "description", "country", "production",
                  "cur_parts", "total_parts", "plan_date", "entry_type"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].required = False
        self.fields['alt_title'].required = False
        self.fields['add_date'].required = False
        self.fields['fin_date'].required = False
        self.fields['description'].required = False
        self.fields['country'].required = False
        self.fields['production'].required = False
        self.fields['cur_parts'].required = False
        self.fields['total_parts'].required = False
        self.fields['plan_date'].required = False
        self.fields['entry_type'].required = False
        self.fields['date_selection'].required = False

    def clean_title(self):
        title = self.cleaned_data.get('title').strip()
        if not title:
            raise ValidationError("Please enter title.")
        return title

    def clean_description(self):
        description = self.cleaned_data.get('description').strip()
        if not description:
            raise ValidationError("Please enter description.")
        return description

    def clean_country(self):
        country = self.cleaned_data.get('country').strip()
        if not country:
            raise ValidationError("Please enter country.")
        return country

    def clean_production(self):
        production = self.cleaned_data.get('production').strip()
        if not production:
            raise ValidationError("Please enter production.")
        return production

    def clean_entry_type(self):
        entry_type = self.cleaned_data.get('entry_type')
        if not entry_type:
            raise ValidationError("Please enter type.")
        return entry_type

    def clean_total_parts(self):
        cur_parts = self.cleaned_data.get('cur_parts')
        total_parts = self.cleaned_data.get('total_parts')
        if cur_parts and total_parts and cur_parts > total_parts:
            raise ValidationError("Invalid current parts")
        return total_parts

    def clean_fin_date(self):
        fin_date = self.cleaned_data.get('fin_date')
        add_date = self.cleaned_data.get('add_date')
        if add_date and fin_date:
            if add_date > fin_date:
                raise ValidationError("Finale date is not valid")
        elif fin_date:
            raise ValidationError("Start date is not valid")
        return fin_date

    def clean_date_selection(self):
        date_selection = self.cleaned_data.get('date_selection')
        if not date_selection:
            raise ValidationError("Select date")
        elif date_selection == 'confirmed':
            add_date = self.cleaned_data.get('add_date')
            if not add_date:
                raise ValidationError("Select start date")
        return date_selection
