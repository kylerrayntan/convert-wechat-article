"""Explicit OMML subset. Unknown constructs fail rather than silently flatten."""
M='http://schemas.openxmlformats.org/officeDocument/2006/math'
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS={'m':M,'w':W}
class Unsupported(ValueError): pass
def local(n): return n.tag.rsplit('}',1)[-1]
def value(n, default=None): return default if n is None else n.get('{'+M+'}val',default)
def enabled(n):
    if n is None:return False
    v=value(n,'1')
    if v not in ('0','1','true','false','on','off'):raise Unsupported('invalid math boolean '+v)
    return v in ('1','true','on')
def text_tex(s):
    if '^' in s:raise Unsupported('literal caret in math needs explicit handling')
    escapes={'\\':r'\backslash{}','{':r'\{','}':r'\}','_':r'\_','%':r'\%','#':r'\#','&':r'\&','$':r'\$','^':r'\hat{}','~':r'\sim '}
    symbols={'δ':r'\delta ','θ':r'\theta ','Δ':r'\Delta ','Φ':r'\Phi ','∘':r'\circ ','−':'-','∠':r'\angle ','≈':r'\approx ','ℛ':r'\mathcal{R}','、':r'\text{、}','π':r'\pi ','α':r'\alpha ','β':r'\beta ','γ':r'\gamma ','ω':r'\omega ','Ω':r'\Omega ','η':r'\eta ','λ':r'\lambda ','μ':r'\mu ','σ':r'\sigma ','τ':r'\tau ','φ':r'\phi ','ψ':r'\psi ','≤':r'\le ','≥':r'\ge ','≠':r'\ne ','∞':r'\infty ','∝':r'\propto ','×':r'\times ','·':r'\cdot '}
    return ''.join(escapes.get(c,symbols.get(c,c)) for c in s)
def convert(n):
    if n is None:return ''
    k=local(n)
    def c(key):return convert(n.find('m:'+key,NS))
    if k=='r':
        if any(local(x) not in {'rPr','t'} for x in n):raise Unsupported('unsupported OMML run child')
        s=text_tex(''.join(t.text or '' for t in n.findall('m:t',NS)))
        sty=value(n.find('m:rPr/m:sty',NS));scr=value(n.find('m:rPr/m:scr',NS))
        if scr not in (None,'roman','script'):raise Unsupported('unsupported math font script: '+scr)
        if scr=='script' and r'\mathcal' not in s:s=r'\mathcal{'+s+'}'
        if sty=='p' or enabled(n.find('m:rPr/m:nor',NS)):s=r'\mathrm{'+s+'}'
        elif sty in ('b','bi'):s=r'\boldsymbol{'+s+'}'
        elif sty not in (None,'i'):raise Unsupported('unsupported math style')
        return s
    if k=='f':
        typ=value(n.find('m:fPr/m:type',NS),'bar')
        if typ!='bar':raise Unsupported('unsupported fraction type: '+typ)
        return r'\frac{'+c('num')+'}{'+c('den')+'}'
    if k in ('sSub','sSup','sSubSup'):
        s='{'+c('e')+'}'
        if k in ('sSub','sSubSup'):s+='_{'+c('sub')+'}'
        if k in ('sSup','sSubSup'):s+='^{'+c('sup')+'}'
        return s
    if k=='bar':
        return ('\\underline{' if value(n.find('m:barPr/m:pos',NS))=='bot' else '\\overline{')+c('e')+'}'
    if k=='d':
        if len(n.findall('m:e',NS))!=1:raise Unsupported('multi-element delimiter')
        def delim(key,default):
            v=value(n.find('m:dPr/m:'+key,NS),default) or '.'
            options={'(': '(',')':')','[':'[',']':']','{':r'\{','}':r'\}','|':'|','‖':r'\Vert ','.':'.'}
            if v not in options:raise Unsupported('unsupported delimiter '+v)
            return options[v]
        return r'\left'+delim('begChr','(')+c('e')+r'\right'+delim('endChr',')')
    if k in ('oMath','box','e','num','den','sub','sup'):
        if k=='box':
            props=n.find('m:boxPr',NS)
            if props is not None and any(local(x)!='ctrlPr' for x in props):raise Unsupported('decorated OMML box')
        return ''.join(convert(x) for x in n if x.tag.startswith('{'+M+'}') and not local(x).endswith('Pr'))
    raise Unsupported('unsupported OMML node: '+k)
def check_structure(n):
    # Reject unhandled properties that alter layout/meaning (including hidden degree, limits).
    allowed={'rPr':{'sty','nor','scr','ctrlPr'},'boxPr':{'ctrlPr'},'fPr':{'type','ctrlPr'},'sSubPr':{'ctrlPr'},'sSupPr':{'ctrlPr'},'sSubSupPr':{'ctrlPr'},'barPr':{'pos','ctrlPr'},'dPr':{'begChr','endChr','grow','ctrlPr'}}
    for x in n.iter():
        if not x.tag.startswith('{'+M+'}'):continue
        k=local(x)
        if k.endswith('Pr') and k!='ctrlPr':
            if k not in allowed:raise Unsupported('unsupported math properties '+k)
            for child in x:
                if local(child) not in allowed[k]:raise Unsupported('unsupported math property '+local(child))

    expressions={'r','box','f','sSub','sSup','sSubSup','bar','d'}
    schema={'box':({'e'},{'boxPr'}),'f':({'num','den'},{'fPr'}),'sSub':({'e','sub'},{'sSubPr'}),'sSup':({'e','sup'},{'sSupPr'}),'sSubSup':({'e','sub','sup'},{'sSubSupPr'}),'bar':({'e'},{'barPr'}),'d':({'e'},{'dPr'})}
    def visit(x):
        k=local(x)
        if x.tag=='{'+W+'}rPr':return
        if not x.tag.startswith('{'+M+'}'):raise Unsupported('foreign node in math '+k)
        if k.endswith('Pr') or k=='ctrlPr':return
        if k=='t':
            if list(x):raise Unsupported('nested math text')
            return
        children=[local(y) for y in x]
        if k in schema:
            required,optional=schema[k]
            if any(children.count(y)!=1 for y in required) or any(children.count(y)>1 for y in optional) or any(y not in required|optional for y in children):raise Unsupported('malformed math structure '+k)
        elif k in ('oMath','e','num','den','sub','sup'):
            if not any(y in expressions for y in children) or any(y not in expressions|{'ctrlPr'} for y in children):raise Unsupported('empty or unsupported math container '+k)
        elif k=='r':
            if not x.findall('m:t',NS) or any(y not in ('rPr','t') for y in children):raise Unsupported('malformed math run')
        else:raise Unsupported('unsupported math node '+k)
        if k=='bar' and value(x.find('m:barPr/m:pos',NS),'top') not in ('top','bot'):raise Unsupported('invalid bar position')
        if k=='d':
            grow=x.find('m:dPr/m:grow',NS)
            if grow is not None and not enabled(grow):raise Unsupported('non-growing delimiter needs explicit handling')
        for child in x:visit(child)
    visit(n)
