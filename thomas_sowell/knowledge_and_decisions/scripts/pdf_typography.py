"""Chinese punctuation and Western word wrapping, reused from the project reading PDFs."""
import unicodedata
import reportlab.platypus.paragraph as rl_paragraph
from reportlab.platypus import Paragraph

def chinese_frag_split(frags,maxWidths,calcBounds,encoding='utf8'):
    U=[]
    for frag in frags:
        text=frag.text.decode(encoding) if isinstance(frag.text,bytes) else frag.text
        U.extend(rl_paragraph.cjkU(ch,frag,encoding) for ch in text or [''])
    cannot_start=set('，。；：！？、）》〉】」』〕］％‰…,.!?:;)]}’”')
    cannot_end=set('（《〈【「『〔［([{‘“')
    n=len(U);prev=['']*n;next_char=['']*n;p=''
    for j,u in enumerate(U):
        if u:p=str(u)
        prev[j]=p
    p=''
    for j in range(n-1,-1,-1):
        next_char[j]=p
        if U[j]:p=str(U[j])
    def allowed(j):
        if j>=n:return True
        a=prev[j-1] if j else '';b=next_char[j-1] if j else str(U[0])
        if not a or not b:return True
        if (a in '-/' and b.isdigit()) or (b in '-/' and a.isdigit()):return False
        if b in cannot_start or a in cannot_end or unicodedata.category(b).startswith('M'):return False
        # Keep an in-text superscript with the words it annotates.
        k=j
        while k<n and not U[k]:k+=1
        if k<n and getattr(U[k].frag,'rise',0)>0:return False
        return a.isspace() or b.isspace() or ord(a)>=0x2e80 or ord(b)>=0x2e80 or a in '-/'
    lines=[];start=0
    while start<n:
        width=maxWidths[min(len(lines),len(maxWidths)-1)];used=0;j=start;last=None;forced=False
        while j<n:
            u=U[j];w=u.width
            if hasattr(w,'normalizedValue'):w._normalizer=width;w=w.normalizedValue(width)
            if hasattr(u.frag,'lineBreak'):
                j+=1;forced=True;break
            if used+w>width+.0001 and j>start:break
            used+=w;j+=1
            if allowed(j):last=j
        if j<n and not forced and last and last>start:j=last
        if j<=start:j=start+1
        chunk=U[start:j]
        while chunk and str(chunk[-1]).isspace() and not hasattr(chunk[-1].frag,'cbDefn'):chunk.pop()
        used=sum(float(u.width) if not hasattr(u.width,'normalizedValue') else u.width.normalizedValue(width) for u in chunk)
        if chunk:lines.append(rl_paragraph.makeCJKParaLine(chunk,width,used,width-used,forced,calcBounds))
        start=j
        while start<n and str(U[start]).isspace() and not hasattr(U[start].frag,'cbDefn'):start+=1
    return rl_paragraph.ParaLines(kind=1,lines=lines)
rl_paragraph.cjkFragSplit=chinese_frag_split
_original_break_lines=Paragraph.breakLinesCJK

def all_chinese_lines(self,maxWidths):
    if not self.frags:return _original_break_lines(self,maxWidths)
    if not isinstance(maxWidths,(list,tuple)):maxWidths=[maxWidths]
    self.height=0
    rl_paragraph._handleBulletWidth(self.bulletText,self.style,maxWidths)
    if hasattr(self,'blPara') and getattr(self,'_splitpara',0):return self.blPara
    auto=getattr(self,'autoLeading',getattr(self.style,'autoLeading',''))
    return chinese_frag_split(self.frags,maxWidths,auto not in ('','off'))
Paragraph.breakLinesCJK=all_chinese_lines
