import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import startup

class InstallerContractTests(unittest.TestCase):
 def test_installed_startup_targets_exe_without_python_requirement(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'bundle.json').write_text('{}');(root/'NAVA AI.exe').write_bytes(b'MZ')
   with patch.object(startup,'ROOT',root):
    target=startup.expected()
    self.assertEqual(target['target'],str(root/'NAVA AI.exe'));self.assertEqual(target['arguments'],'--startup')
 def test_source_launch_still_uses_its_existing_environment(self):
  with tempfile.TemporaryDirectory() as folder:
   with patch.object(startup,'ROOT',Path(folder)):
    self.assertTrue(startup.expected()['target'].endswith('pythonw.exe'))
    self.assertIn('nava.py',startup.expected()['arguments'])
 def test_package_allowlist_keeps_active_assets_and_excludes_orphans(self):
  import importlib.util
  spec=importlib.util.spec_from_file_location('nava_payload_build',Path(__file__).parent/'packaging/build.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
  self.assertEqual(set(builder.MODELS),{'vosk-model-small-en-us-0.15','whisper-base.en','punctuation-en'})
  dependencies=builder.required_distributions()
  self.assertIn('vosk',dependencies);self.assertIn('faster-whisper',dependencies);self.assertIn('rapidocr-onnxruntime',dependencies)
  self.assertFalse(any('openvino' in name or 'torch' in name for name in dependencies))

if __name__=='__main__':unittest.main()
