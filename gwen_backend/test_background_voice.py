import io,time,threading,unittest,wave
from command_voice import CommandVoice
from task_feedback import BackgroundPresenter,SoundCues,cue_wave

class Panel:
    def __init__(self):self.hidden=False
    def withdraw(self):self.hidden=True
    def deiconify(self):raise AssertionError('Task feedback must not show the panel')
    def lift(self):raise AssertionError('Task feedback must not raise a window')
    def focus_force(self):raise AssertionError('Task feedback must not take focus')
    def focus_set(self):raise AssertionError('Task feedback must not change focus')

class BackgroundVoiceTests(unittest.TestCase):
    def test_listen_latches_across_commands_stop_errors_and_time(self):
        from unittest.mock import patch
        session=CommandVoice();ctx={'grid_active':True,'labels':['FG']}
        self.assertEqual(session.route({'text':'Gwen listen','confidence':.99})['control'],'handsfree')
        with patch('command_voice.time.monotonic',return_value=time.monotonic()+86400):
            for _ in range(5):
                self.assertEqual(session.route({'text':'FG','confidence':.99},ctx)['kind'],'command')
                self.assertEqual(session.route({'text':'stop','confidence':.99})['control'],'stop')
                self.assertTrue(session.handsfree)
                self.assertEqual(session.route({'text':'click FB','confidence':.99},ctx)['kind'],'review')
                self.assertTrue(session.handsfree)
        self.assertEqual(session.route({'text':'Gwen sleep','confidence':.99})['control'],'sleep')
        self.assertEqual(session.route({'text':'FG','confidence':.99},ctx)['kind'],'ignore')
    def test_task_and_review_feedback_never_restore_or_focus_panel(self):
        from unittest.mock import Mock
        panel=Panel();cues=Mock();presenter=BackgroundPresenter(panel,cues)
        for result in ('Done.','Click completed at FG.','Task failed: unavailable','Stopped'):
            presenter.begin();presenter.finished(result);self.assertTrue(panel.hidden)
        presenter.review();self.assertEqual(cues.notify.call_count,5)
    def test_cues_are_short_pcm_audio(self):
        for kind in ('complete','attention'):
            with wave.open(io.BytesIO(cue_wave(kind)),'rb') as sound:
                self.assertEqual(sound.getnchannels(),1);self.assertEqual(sound.getsampwidth(),2)
                self.assertLess(sound.getnframes()/sound.getframerate(),.3)
    def test_cue_playback_is_async_and_gates_microphone(self):
        entered=threading.Event();finish=threading.Event();played=[]
        def play(data):played.append(data);entered.set();finish.wait(1)
        cues=SoundCues(play=play)
        try:
            cues.notify();self.assertTrue(entered.wait(1));self.assertTrue(cues.speaking.is_set())
            finish.set();deadline=time.monotonic()+1
            while cues.speaking.is_set() and time.monotonic()<deadline:time.sleep(.01)
            self.assertFalse(cues.speaking.is_set());self.assertEqual(len(played),1)
        finally:finish.set();cues.close()
    def test_cancel_pending_can_flush_without_restarting_audio_device(self):
        from speech import VoiceEngine
        engine=VoiceEngine(lambda *_:None,lambda _:None,lambda:{})
        engine.audio.put(('old',0));engine.cancel_pending(restart=False)
        self.assertEqual(engine.epoch,1);self.assertTrue(engine.audio.empty());self.assertFalse(engine.restart.is_set())
        engine.close()
    def test_saved_handsfree_state_survives_application_restart(self):
        session=CommandVoice({'handsfree':True})
        self.assertEqual(session.route({'text':'scroll down','confidence':.99})['kind'],'command')

if __name__=='__main__':unittest.main()
