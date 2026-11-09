"""Offline punctuation restoration; no generation, paraphrasing or word replacement."""
import difflib,re
from functools import lru_cache
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def raw_dictation(text):
    # Keep decimal numbers, URLs and punctuation inside words; remove ASR's
    # sentence/clause marks at whitespace boundaries rather than invent breaks.
    protected=[]
    def keep(match):
        protected.append(match[0]);return '\ue000'+str(len(protected)-1)+'\ue001'
    text=re.sub(r'(?:https?://|www\.)\S+|\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|(?:\b[A-Za-z]\.){2,}',keep,text)
    text=re.sub(r'[.,!?;:]+(?=\s|$|["”])','',text)
    for i,value in enumerate(protected):text=text.replace('\ue000'+str(i)+'\ue001',value.rstrip('.,!?;:') if value.startswith(('http','www.')) else value)
    return text.strip()


def significant(text):
    return ''.join(c for c in text if c.isalnum() or c in "_'’-" ).casefold()


def edits(before,after):
    expected=re.sub(r'\b(?:open|start) quote\b\s*(.+?)\s*\b(?:close|end) quote\b',lambda m:'"'+m[1]+'"',before,flags=re.I)
    if significant(expected)!=significant(after):raise ValueError('Punctuation would change words. Nothing was edited.')
    return [(a,b,after[c:d]) for op,a,b,c,d in difflib.SequenceMatcher(None,before,after,autojunk=False).get_opcodes() if op!='equal']


def add_quotation_marks(text):
    # Explicit paired quote markers are reliable, unlike guessing every use of
    # reported speech. Unpaired markers stay untouched for the user to finish.
    text=re.sub(r'\b(?:open|start) quote\b\s*(.+?)\s*\b(?:close|end) quote\b',lambda m:'"'+m[1].strip(' ,')+'"',text,flags=re.I)
    pattern=r'\b(said|replied|whispered|shouted)\s*,?\s+((?:hello|hi|yes|no|please|thank you|good morning)\b[^.!?\n]*[.!?]?)'
    def quote(match):
        speech=match[2].strip()
        if re.match(r'(?:hello|hi)\s+to\b|no\s+(?:one|longer|more)\b',speech,re.I):return match[0]
        return match[1]+', "'+speech[0].upper()+speech[1:]+'"'
    return re.sub(pattern,quote,text,flags=re.I)


class Punctuator:
    def __init__(self,directory=None):
        import onnxruntime as ort
        import sentencepiece as sp
        self.path=Path(directory or ROOT/'models'/'punctuation-en')
        options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
        self.session=ort.InferenceSession(str(self.path/'punct_cap_seg_en.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
        self.tokenizer=sp.SentencePieceProcessor(model_file=str(self.path/'spe_32k_lc_en.model'))

    def paragraph(self,text,stop=None):
        import numpy as np
        if not text.strip():return text
        tokens=list(self.tokenizer.encode(text.lower(),return_type='proto').pieces)
        ids=[token.id for token in tokens]
        predictions={}
        # Overlap supplies context at boundaries; keep each token's most
        # central prediction. Only classifier labels are used, never new words.
        for start in range(0,len(ids),222):
            if stop and stop.is_set():raise InterruptedError('Stopped punctuation')
            chunk=ids[start:start+254]
            batch=np.asarray([[self.tokenizer.bos_id()]+chunk+[self.tokenizer.eos_id()]],dtype=np.int64)
            outputs=self.session.run(None,{'input_ids':batch})
            labels=outputs[1][0,1:len(chunk)+1]
            for i,label in enumerate(labels):
                priority=min(i,len(chunk)-1-i)
                if start+i not in predictions or priority>predictions[start+i][0]:predictions[start+i]=(priority,int(label))
            if start+254>=len(ids):break
        out=[]
        protected_spans=[m.span() for m in re.finditer(r'(?:https?://|www\.)\S+|\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b\d+(?:[.,:]\d+)+\b',text)]
        for index,token in enumerate(ids):
            piece=tokens[index].surface
            label=predictions[index][1]
            if piece.strip() in ('"','”') and (piece.strip()=='”' or text[:tokens[index].begin].count('"')%2):
                piece={2:'.',4:'?'}.get(label,'')+piece;label=0
            elif not any(c.isalnum() for c in piece):label=0
            if any(a<tokens[index].end<b for a,b in protected_spans):label=0
            if label==1:out.extend(ch+'.' if ch.isalnum() else ch for ch in piece)
            else:out.append(piece);out.append({2:'.',3:',',4:'?'}.get(label,''))
        result=''.join(out).strip()
        result=re.sub(r'([.,?])(?:[.,?])+',r'\1',result)
        if significant(text)!=significant(result):raise ValueError('The punctuation model could not preserve all words. Nothing was edited.')
        letters=iter(c for c in text if c.isalnum())
        result=''.join(next(letters) if c.isalnum() else c for c in result)
        result=re.sub(r'(^|[.!?]\s+)([a-z])',lambda m:m[1]+m[2].upper(),result)
        # Keep user-supplied quotes, URLs and numbers intact.
        for protected in re.findall(r'(?:https?://|www\.)\S+|\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b\d+(?:[.,:]\d+)+\b',text):
            if protected not in result:raise ValueError('Punctuation could alter a URL, email or number. Nothing was edited.')
        return result

    def restore(self,text,stop=None):
        if len(text)>20000:raise ValueError('Select at most 20,000 characters to punctuate.')
        source=text
        text=re.sub(r'\b(?:open|start) quote\b\s*(.+?)\s*\b(?:close|end) quote\b',lambda m:'"'+m[1].strip()+'"',text,flags=re.I)
        parts=re.split(r'([\r\n\t\x07]+)',text);restored=[]
        for part in parts:
            if not part or re.fullmatch(r'[\r\n\t\x07]+',part):restored.append(part);continue
            leading=re.match(r'^\s*',part)[0];trailing=re.search(r'\s*$',part)[0]
            body=part.strip();restored.append(leading+self.paragraph(body,stop)+trailing)
        result=''.join(restored)
        # Automatic direct-speech quotes preserve words and remain conservative.
        result=add_quotation_marks(result)
        result=re.sub(r'(?<=\w)(["”])([.!?])',r'\2\1',result)
        result=re.sub(r'(?<!\w)(["“])([a-z])',lambda m:m[1]+m[2].upper(),result)
        if significant(text)!=significant(result):
            # Paired spoken quote markers are intentional markup, not prose.
            expected=re.sub(r'\b(?:open|start|close|end) quote\b','',text,flags=re.I)
            if significant(expected)!=significant(result):raise ValueError('Punctuation would change words. Nothing was edited.')
        edits(source,result)
        return result


@lru_cache(maxsize=1)
def engine():return Punctuator()
