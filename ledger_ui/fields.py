from django import forms

class ListTextWidget(forms.TextInput):

    template_name = 'ledger_ui/widgets/list_text.html'

    def __init__(self, data_list, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._name = name
        self._list = data_list
        self.attrs['list'] ='list__{}'.format(self._name)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['data_list_id'] = self._name
        context['data_list'] = self._list
        return context
