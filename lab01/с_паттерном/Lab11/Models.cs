using System;
using System.IO;
using System.Threading.Tasks;
using System.Windows.Media;

namespace Lab11
{
    public abstract class DrumKit
    {
        protected string[] paths;

        public abstract string Name { get; }

        public abstract void PlayTrack(int trackIndex);

        public string GetPath(int trackIndex)
        {
            return paths[trackIndex];
        }

        protected void PlaySound(string relativePath)
        {
            var player = new MediaPlayer();
            string fullPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, relativePath);
            player.Open(new Uri(fullPath, UriKind.Absolute));
            player.Play();
        }
    }

    public class RockKit : DrumKit
    {
        public override string Name => "Acoustic Rock (Polyphonic)";

        public RockKit()
        {
            paths = new string[]
            {
                @"Samples\Rock\kick.wav",
                @"Samples\Rock\snare.wav",
                @"Samples\Rock\hat.wav",
                @"Samples\Rock\clap.wav"
            };
        }

        public override void PlayTrack(int trackIndex)
        {
            PlaySound(paths[trackIndex]);
        }
    }

    public class TrapKit : DrumKit
    {
        private MediaPlayer activeHiHat;

        public override string Name => "Trap 808 (Choked Hat)";

        public TrapKit()
        {
            paths = new string[]
            {
                @"Samples\Trap\kick.wav",
                @"Samples\Trap\snare.wav",
                @"Samples\Trap\hat.wav",
                @"Samples\Trap\clap.wav"
            };
        }

        public override void PlayTrack(int trackIndex)
        {
            if (trackIndex == 2)
            {
                if (activeHiHat != null)
                {
                    activeHiHat.Stop();
                }
                activeHiHat = new MediaPlayer();
                string fullPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, paths[trackIndex]);
                activeHiHat.Open(new Uri(fullPath, UriKind.Absolute));
                activeHiHat.Play();
            }
            else
            {
                PlaySound(paths[trackIndex]);
            }
        }
    }

    public class SynthwaveKit : DrumKit
    {
        public override string Name => "Synthwave (Snare Echo)";

        public SynthwaveKit()
        {
            paths = new string[]
            {
                @"Samples\Synthwave\kick.wav",
                @"Samples\Synthwave\snare.wav",
                @"Samples\Synthwave\hat.wav",
                @"Samples\Synthwave\clap.wav"
            };
        }

        public override void PlayTrack(int trackIndex)
        {
            PlaySound(paths[trackIndex]);

            if (trackIndex == 1)
            {
                PlayEchoAsync(paths[trackIndex]);
            }
        }

        private async void PlayEchoAsync(string path)
        {
            await Task.Delay(200);
            PlaySound(path);
        }
    }
}