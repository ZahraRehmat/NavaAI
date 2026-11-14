import asyncio,threading,unittest
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from unittest.mock import Mock,AsyncMock,patch
from system_media import browser_title,source_matches,execute,find_session,video_title_candidates
from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionPlaybackStatus as Status


class WindowsMediaTests(unittest.TestCase):
    def session(self):
        info=SimpleNamespace(playback_status=Status.PAUSED,playback_rate=1,
            controls=SimpleNamespace(is_pause_enabled=True,is_play_enabled=True,is_playback_position_enabled=True))
        timeline=SimpleNamespace(position=timedelta(seconds=30),start_time=timedelta(),end_time=timedelta(seconds=100),last_updated_time=datetime.now(timezone.utc))
        session=Mock();session.get_playback_info.return_value=info;session.get_timeline_properties.return_value=timeline
        async def play():info.playback_status=Status.PLAYING;return True
        async def pause():info.playback_status=Status.PAUSED;return True
        async def seek(ticks):timeline.position=timedelta(seconds=ticks/10000000);return True
        session.try_play_async=AsyncMock(side_effect=play);session.try_pause_async=AsyncMock(side_effect=pause);session.try_change_playback_position_async=AsyncMock(side_effect=seek)
        return session,info,timeline

    def test_browser_and_exact_video_binding(self):
        for title in ('Example - YouTube - Google Chrome','Example - YouTube - Personal - Microsoft\u200b Edge'):
            self.assertEqual(browser_title({'title':title}),'Example')
        self.assertTrue(source_matches('Chrome','chrome'));self.assertFalse(source_matches('Chrome','msedge'))
        self.assertTrue(source_matches('MSEdge','msedge'));self.assertFalse(source_matches('Spotify','chrome'))

    def test_notification_count_matches_real_metadata_without_title_guessing(self):
        title='Do Souvenir Plots Make You a Scottish LORD?'
        context={'title':'(1) '+title+' - YouTube - Google Chrome'}
        correct=Mock(source_app_user_model_id='Chrome')
        correct.try_get_media_properties_async=AsyncMock(return_value=SimpleNamespace(title=title))
        other=Mock(source_app_user_model_id='Chrome')
        other.try_get_media_properties_async=AsyncMock(return_value=SimpleNamespace(title='Other video'))
        edge=Mock(source_app_user_model_id='MSEdge')
        edge.try_get_media_properties_async=AsyncMock(return_value=SimpleNamespace(title=title))
        manager=Mock();manager.get_sessions.return_value=[other,edge,correct]
        factory=Mock(request_async=AsyncMock(return_value=manager))
        with patch('winrt.windows.media.control.GlobalSystemMediaTransportControlsSessionManager',factory):
            self.assertIs(asyncio.run(find_session(context)),correct)
            manager.get_sessions.return_value=[correct,correct]
            self.assertIsNone(asyncio.run(find_session(context)))
            manager.get_sessions.return_value=[other]
            self.assertIsNone(asyncio.run(find_session(context)))
        # Don't discard the number when it is genuinely part of a video title.
        self.assertIn('1example',video_title_candidates({'title':'(1) Example - YouTube - Google Chrome'}))
        self.assertEqual(video_title_candidates({'title':'(1) Example - Google Chrome'}),{'1example'})

    def test_pause_resume_are_explicit_and_idempotent(self):
        s,info,_=self.session();guard=Mock()
        asyncio.run(execute(s,{'action':'media_pause'},guard));s.try_pause_async.assert_not_called()
        asyncio.run(execute(s,{'action':'media_play'},guard));asyncio.run(execute(s,{'action':'media_play'},guard))
        s.try_play_async.assert_awaited_once();self.assertEqual(info.playback_status,Status.PLAYING)
        asyncio.run(execute(s,{'action':'media_pause'},guard));s.try_pause_async.assert_awaited_once()

    def test_exact_five_ten_second_seeks_and_bounds(self):
        s,_,timeline=self.session()
        for seconds,expected in ((5,35),(-5,30),(10,40),(-10,30)):
            asyncio.run(execute(s,{'action':'media_seek','seconds':seconds},Mock()))
            self.assertEqual(timeline.position.total_seconds(),expected)
        timeline.position=timedelta(seconds=98)
        asyncio.run(execute(s,{'action':'media_seek','seconds':5},Mock()))
        self.assertEqual(timeline.position.total_seconds(),100)
        with self.assertRaises(ValueError):asyncio.run(execute(s,{'action':'media_seek','seconds':500},Mock()))

    def test_changed_app_and_rejected_api_never_trigger_another_input(self):
        s,_,_=self.session();guard=Mock(side_effect=ValueError('changed'))
        with self.assertRaises(ValueError):asyncio.run(execute(s,{'action':'media_play'},guard))
        s.try_play_async.assert_not_called()
        s.try_play_async=AsyncMock(return_value=False)
        with self.assertRaisesRegex(ValueError,'No toggle fallback'):asyncio.run(execute(s,{'action':'media_play'},Mock()))
        s.try_play_async.assert_awaited_once()


if __name__=='__main__':unittest.main()
