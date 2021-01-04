from django import forms

class SortMethod(forms.Form):
	Choice = [('default', 'Default'),
				('relevance', 'Relevance'),
				('like', 'Like')]
	sort = forms.CharField(widget = forms.RadioSelect(choices = Choice), required = False)
	channel		= forms.CharField(required = True, widget=forms.TextInput(attrs={'placeholder': '    Channel Name'}))
	comment = forms.CharField(required = True, widget=forms.TextInput(attrs={'placeholder': '    Key Words'}))
	# def __init__(self, *args, **kwargs):
	# 	super(SortMethod, self).__init__(*args, **kwargs)
	# 	self.fields['sort'].choices = [('default', 'Default'),
	# 									('relevance', 'Relevance'),
	#