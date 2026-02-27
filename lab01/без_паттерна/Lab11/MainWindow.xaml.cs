using System;
using System.Collections.Generic;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Media;
using System.Windows.Shapes;
using System.Windows.Threading;
using Microsoft.Win32;
using NAudio.Wave;
using NAudio.Wave.SampleProviders;
using System.Threading.Tasks;
using Lab11;

namespace Lab11
{
    public partial class MainWindow : Window
    {
        private AudioSample[] currentSamples = new AudioSample[4];
        private AudioSample activeTrapHiHat;
        private string currentGenre = "Rock";

        private DispatcherTimer timer;
        private ToggleButton[,] stepButtons;
        private Rectangle[] stepIndicators;
        private bool[][] gridData;
        private int currentStep = 0;
        private int stepsCount = 16;
        private const int TracksCount = 4;

        public MainWindow()
        {
            InitializeComponent();
            gridData = new bool[TracksCount][];
            for (int i = 0; i < TracksCount; i++) gridData[i] = new bool[64];

            BuildChannelStrips();
            timer = new DispatcherTimer();
            timer.Tick += EngineTick;

            double stepDurationMs = (60000.0 / SliderBpm.Value) / 4.0;
            timer.Interval = TimeSpan.FromMilliseconds(stepDurationMs);

            ComboKits.SelectedIndex = 0;
        }

        private void ComboKits_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (ComboKits.SelectedIndex == 0)
            {
                currentGenre = "Rock";
                currentSamples[0] = new AudioSample(@"Samples\Rock\kick.wav");
                currentSamples[1] = new AudioSample(@"Samples\Rock\snare.wav");
                currentSamples[2] = new AudioSample(@"Samples\Rock\hat.wav");
                currentSamples[3] = new AudioSample(@"Samples\Rock\clap.wav");
                TxtStatus.Text = "Mode: Acoustic Rock";
            }
            else if (ComboKits.SelectedIndex == 1)
            {
                currentGenre = "Trap";
                currentSamples[0] = new AudioSample(@"Samples\Trap\kick.wav");
                currentSamples[1] = new AudioSample(@"Samples\Trap\snare.wav");
                currentSamples[2] = new AudioSample(@"Samples\Trap\hat.wav");
                currentSamples[3] = new AudioSample(@"Samples\Trap\clap.wav");
                TxtStatus.Text = "Mode: Trap 808";
            }
            else if (ComboKits.SelectedIndex == 2)
            {
                currentGenre = "Synthwave";
                currentSamples[0] = new AudioSample(@"Samples\Synthwave\kick.wav");
                currentSamples[1] = new AudioSample(@"Samples\Synthwave\snare.wav");
                currentSamples[2] = new AudioSample(@"Samples\Synthwave\hat.wav");
                currentSamples[3] = new AudioSample(@"Samples\Synthwave\clap.wav");
                TxtStatus.Text = "Mode: Synthwave";
            }
        }

        private void EngineTick(object sender, EventArgs e)
        {
            stepIndicators[currentStep == 0 ? stepsCount - 1 : currentStep - 1].Fill = Brushes.Transparent;
            stepIndicators[currentStep].Fill = Brushes.Orange;

            for (int t = 0; t < TracksCount; t++)
            {
                if (gridData[t][currentStep])
                {
                    if (currentGenre == "Trap" && t == 2)
                    {
                        if (activeTrapHiHat != null) activeTrapHiHat.Stop();
                        activeTrapHiHat = currentSamples[t];
                        activeTrapHiHat.Play();
                    }
                    else if (currentGenre == "Synthwave" && t == 1)
                    {
                        currentSamples[t].Play();
                        PlayEchoEffect(currentSamples[t].FilePath);
                    }
                    else
                    {
                        currentSamples[t]?.Play();
                    }
                }
            }

            currentStep = (currentStep + 1) % stepsCount;
        }

        private async void PlayEchoEffect(string path)
        {
            await Task.Delay(200);
            var echoPlayer = new MediaPlayer();
            echoPlayer.Open(new Uri(path, UriKind.Absolute));
            echoPlayer.Volume = 0.3;
            echoPlayer.Play();
        }

        private void BuildChannelStrips()
        {
            TracksPanel.Children.Clear();
            stepButtons = new ToggleButton[TracksCount, stepsCount];
            stepIndicators = new Rectangle[stepsCount];
            string[] names = { "KICK", "SNARE", "HI-HAT", "CLAP" };
            Grid indGrid = new Grid { Margin = new Thickness(100, 0, 0, 5) };
            for (int i = 0; i < stepsCount; i++)
            {
                indGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(35) });
                var r = new Rectangle { Height = 4, Fill = Brushes.Transparent, Margin = new Thickness(2) };
                Grid.SetColumn(r, i); indGrid.Children.Add(r); stepIndicators[i] = r;
            }
            TracksPanel.Children.Add(indGrid);
            for (int t = 0; t < TracksCount; t++)
            {
                Grid g = new Grid { Height = 50, Margin = new Thickness(0, 0, 0, 10) };
                g.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(100) });
                for (int s = 0; s < stepsCount; s++) g.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(35) });
                var lbl = new TextBlock { Text = names[t], Foreground = Brushes.White, VerticalAlignment = VerticalAlignment.Center };
                Grid.SetColumn(lbl, 0); g.Children.Add(lbl);
                for (int s = 0; s < stepsCount; s++)
                {
                    var b = new ToggleButton { Margin = new Thickness(2), Background = new SolidColorBrush(s % 4 == 0 ? Color.FromRgb(170, 170, 170) : Color.FromRgb(210, 210, 210)) };
                    int trk = t, stp = s;
                    b.IsChecked = gridData[trk][stp];
                    b.Checked += (snd, ev) => gridData[trk][stp] = true;
                    b.Unchecked += (snd, ev) => gridData[trk][stp] = false;
                    Grid.SetColumn(b, s + 1); g.Children.Add(b); stepButtons[t, s] = b;
                }
                TracksPanel.Children.Add(g);
            }
        }

        private void ComboSteps_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (ComboSteps.SelectedItem is ComboBoxItem item && int.TryParse(item.Content.ToString(), out int val))
            {
                stepsCount = val; currentStep = 0;
                if (TracksPanel != null) BuildChannelStrips();
            }
        }

        private void BtnPlay_Click(object sender, RoutedEventArgs e) => timer.Start();
        private void BtnStop_Click(object sender, RoutedEventArgs e)
        {
            timer.Stop();
            foreach (var r in stepIndicators) r.Fill = Brushes.Transparent;
            currentStep = 0;
        }

        private void SliderBpm_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if (timer != null)
            {
                timer.Interval = TimeSpan.FromMilliseconds((60000.0 / SliderBpm.Value) / 4.0);
                TxtBpm.Text = Math.Round(SliderBpm.Value).ToString();
            }
        }

        private void BtnExport_Click(object sender, RoutedEventArgs e)
        {
            var sfd = new SaveFileDialog { Filter = "MP3 Audio (*.mp3)|*.mp3", DefaultExt = ".mp3" };
            if (sfd.ShowDialog() == true) ExportToMp3(sfd.FileName);
        }

        private void ExportToMp3(string outPath)
        {
            double dur = (60000.0 / SliderBpm.Value) / 4.0;
            var mixer = new MixingSampleProvider(WaveFormat.CreateIeeeFloatWaveFormat(44100, 2));
            var list = new List<IDisposable>();
            try
            {
                for (int t = 0; t < TracksCount; t++)
                {
                    string p = currentSamples[t].FilePath;
                    if (!System.IO.File.Exists(p)) continue;
                    for (int s = 0; s < stepsCount; s++) if (gridData[t][s])
                        {
                            var r = new MediaFoundationReader(p); list.Add(r);
                            ISampleProvider sp = r.ToSampleProvider();
                            if (sp.WaveFormat.Channels == 1) sp = new MonoToStereoSampleProvider(sp);
                            if (sp.WaveFormat.SampleRate != 44100) sp = new WdlResamplingSampleProvider(sp, 44100);
                            mixer.AddMixerInput(new OffsetSampleProvider(sp) { DelayBy = TimeSpan.FromMilliseconds(s * dur) });
                        }
                }
                if (list.Count > 0) MediaFoundationEncoder.EncodeToMp3(mixer.ToWaveProvider(), outPath);
            }
            finally { foreach (var d in list) d.Dispose(); }
        }
    }
}