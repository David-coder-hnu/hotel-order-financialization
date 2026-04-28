with open('credit_model.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("pd = self._dd_to_pd(dd)", "prob_default = self._dd_to_pd(dd)")
content = content.replace("el = pd * lgd", "el = prob_default * lgd")
content = content.replace("'pd': pd,", "'pd': prob_default,")

with open('credit_model.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed pd variable name conflict')
