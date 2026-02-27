using System;
using System.IO;
using System.Windows.Media;

namespace Lab11
{
    public class ProjectFile
    {
        public int Bpm { get; set; }
        public int KitIndex { get; set; }
        public int StepsCount { get; set; }
        public bool[][] GridData { get; set; }
        public double[] TrackVolumes { get; set; }
    }

    public class AudioSample
    {
        private readonly MediaPlayer player;
        public string FilePath { get; private set; }

        public AudioSample(string relativePath)
        {
            player = new MediaPlayer();
            FilePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, relativePath);
            player.Open(new Uri(FilePath, UriKind.Absolute));
            player.Volume = 0.8;
        }

        public void Play()
        {
            player.Position = TimeSpan.Zero;
            player.Play();
        }

        public void Stop()
        {
            player.Stop();
        }

        public void SetVolume(double volume)
        {
            player.Volume = volume;
        }
    }
}