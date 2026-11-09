"""One-time punctuation model download; runtime processing stays offline."""
from pathlib import Path
from huggingface_hub import hf_hub_download

REPO='1-800-BAD-CODE/punctuation_fullstop_truecase_english'
REVISION='b26fd1c40e88678859048898218ea4edcc24c84a'

if __name__=='__main__':
    destination=Path(__file__).resolve().parent/'models'/'punctuation-en'
    destination.mkdir(parents=True,exist_ok=True)
    for name in ('config.yaml','spe_32k_lc_en.model','punct_cap_seg_en.onnx'):
        hf_hub_download(REPO,name,revision=REVISION,local_dir=str(destination))
    (destination/'source_revision.txt').write_text(REPO+'\n'+REVISION+'\n',encoding='utf-8')
    print('Offline punctuation model ready. It loads only when requested.')
