using System;
using System.Collections.Generic;
using System.IO;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Media;
using System.Windows.Shapes;
using System.Windows.Threading;
using DawStudio;
using Lab11;
using Microsoft.VisualBasic;
using Microsoft.Win32;
using NAudio.Wave;
using NAudio.Wave.SampleProviders;

namespace Lab11
{
    public partial class MainWindow : Window
    {
        private List<IKitFactory> factories;
        private DrumKit activeKit;
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


            factories = new List<IKitFactory>
            {
                new TrapKitFactory(),
                new RockKitFactory(),
                new SynthwaveKitFactory()
            };

            foreach (var factory in factories)
            {
                ComboKits.Items.Add(factory.CreateKit().Name);
            }

            BuildChannelStrips();
            timer = new DispatcherTimer();
            timer.Tick += EngineTick;
            SliderBpm_ValueChanged(null, null);
            ComboKits.SelectedIndex = 0;
        }


        private void BuildChannelStrips()
        {
            TracksPanel.Children.Clear();
            stepButtons = new ToggleButton[TracksCount, stepsCount];
            stepIndicators = new Rectangle[stepsCount];
            string[] trackNames = { "KICK", "SNARE", "HI-HAT", "CLAP" };

            Grid indicatorGrid = new Grid { Margin = new Thickness(100, 0, 0, 5) };
            for (int i = 0; i < stepsCount; i++)
            {
                indicatorGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(35) });
                Rectangle rect = new Rectangle { Height = 4, Fill = Brushes.Transparent, Margin = new Thickness(2, 0, 2, 0) };
                Grid.SetColumn(rect, i);
                indicatorGrid.Children.Add(rect);
                stepIndicators[i] = rect;
            }
            TracksPanel.Children.Add(indicatorGrid);

            for (int t = 0; t < TracksCount; t++)
            {
                Grid trackGrid = new Grid { Height = 50, Margin = new Thickness(0, 0, 0, 10) };
                trackGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(100) });

                for (int s = 0; s < stepsCount; s++) trackGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(35) });

                TextBlock label = new TextBlock { Text = trackNames[t], Foreground = Brushes.White, VerticalAlignment = VerticalAlignment.Center, Margin = new Thickness(10, 0, 0, 0) };
                Grid.SetColumn(label, 0);
                trackGrid.Children.Add(label);

                for (int s = 0; s < stepsCount; s++)
                {
                    ToggleButton btn = new ToggleButton { Margin = new Thickness(2) };

                    if (s % 4 == 0) btn.Background = new SolidColorBrush(Color.FromRgb(180, 180, 180));
                    else btn.Background = new SolidColorBrush(Color.FromRgb(220, 220, 220));

                    int trk = t, stp = s;
                    btn.IsChecked = gridData[trk][stp];
                    btn.Checked += (snd, ev) => gridData[trk][stp] = true;
                    btn.Unchecked += (snd, ev) => gridData[trk][stp] = false;

                    Grid.SetColumn(btn, s + 1);
                    trackGrid.Children.Add(btn);
                    stepButtons[t, s] = btn;
                }
                TracksPanel.Children.Add(trackGrid);
            }
        }

        private void ComboKits_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (ComboKits.SelectedIndex >= 0)
            {
                activeKit = factories[ComboKits.SelectedIndex].CreateKit();
                TxtStatus.Text = $"Loaded: {activeKit.Name}";
            }
        }

        private void ComboSteps_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (ComboSteps.SelectedItem is ComboBoxItem item && int.TryParse(item.Content.ToString(), out int newSteps))
            {
                if (newSteps == stepsCount) return;

                bool wasPlaying = timer?.IsEnabled == true;
                timer?.Stop();

                int oldSteps = stepsCount;
                stepsCount = newSteps;

                bool[][] newGrid = new bool[TracksCount][];
                for (int i = 0; i < TracksCount; i++)
                {
                    newGrid[i] = new bool[stepsCount];
                    for (int j = 0; j < Math.Min(oldSteps, stepsCount); j++)
                    {
                        if (gridData != null && gridData[i] != null)
                        {
                            newGrid[i][j] = gridData[i][j];
                        }
                    }
                }
                gridData = newGrid;
                currentStep = 0;

                if (TracksPanel != null) BuildChannelStrips();
                if (wasPlaying) timer?.Start();
            }
        }

        private void BtnPlay_Click(object sender, RoutedEventArgs e) => timer.Start();

        private void BtnStop_Click(object sender, RoutedEventArgs e)
        {
            timer.Stop();
            for (int i = 0; i < stepsCount; i++) stepIndicators[i].Fill = Brushes.Transparent;
            currentStep = 0;
        }

        private void SliderBpm_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if (timer != null && SliderBpm != null)
            {
                double stepDurationMs = (60000.0 / SliderBpm.Value) / 4.0;
                timer.Interval = TimeSpan.FromMilliseconds(stepDurationMs);
                TxtBpm.Text = Math.Round(SliderBpm.Value).ToString();
            }
        }

        private void EngineTick(object sender, EventArgs e)
        {
            int prevStep = currentStep == 0 ? stepsCount - 1 : currentStep - 1;
            stepIndicators[prevStep].Fill = Brushes.Transparent;
            stepIndicators[currentStep].Fill = Brushes.Orange;

            if (activeKit != null)
            {
                for (int t = 0; t < TracksCount; t++)
                {
                    if (gridData[t][currentStep])
                    {
                        activeKit.PlayTrack(t);
                    }
                }
            }

            currentStep = (currentStep + 1) % stepsCount;
        }

        private void BtnExport_Click(object sender, RoutedEventArgs e)
        {
            var sfd = new SaveFileDialog { Filter = "MP3 Audio (*.mp3)|*.mp3", DefaultExt = ".mp3" };
            if (sfd.ShowDialog() == true)
            {
                ExportToMp3(sfd.FileName);
            }
        }

        private void ExportToMp3(string outputPath)
        {
            TxtStatus.Text = "Rendering MP3...";
            double stepDurationMs = (60000.0 / SliderBpm.Value) / 4.0;

            var outputFormat = WaveFormat.CreateIeeeFloatWaveFormat(44100, 2);
            var mixer = new MixingSampleProvider(outputFormat);
            var disposables = new List<IDisposable>();

            try
            {
                for (int t = 0; t < TracksCount; t++)
                {
                    string path = System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory, activeKit.GetPath(t));
                    if (!System.IO.File.Exists(path)) continue;

                    for (int s = 0; s < stepsCount; s++)
                    {
                        if (gridData[t][s])
                        {
                            var reader = new MediaFoundationReader(path);
                            disposables.Add(reader);

                            ISampleProvider provider = reader.ToSampleProvider();

                            if (provider.WaveFormat.Channels == 1)
                            {
                                provider = new MonoToStereoSampleProvider(provider);
                            }

                            if (provider.WaveFormat.SampleRate != 44100)
                            {
                                provider = new WdlResamplingSampleProvider(provider, 44100);
                            }

                            var delay = new OffsetSampleProvider(provider) { DelayBy = TimeSpan.FromMilliseconds(s * stepDurationMs) };
                            mixer.AddMixerInput(delay);

                            if (activeKit is SynthwaveKit && t == 1)
                            {
                                var readerEcho = new MediaFoundationReader(path);
                                disposables.Add(readerEcho);

                                ISampleProvider echoProvider = readerEcho.ToSampleProvider();
                                if (echoProvider.WaveFormat.Channels == 1) echoProvider = new MonoToStereoSampleProvider(echoProvider);
                                if (echoProvider.WaveFormat.SampleRate != 44100) echoProvider = new WdlResamplingSampleProvider(echoProvider, 44100);

                                var echoVol = new VolumeSampleProvider(echoProvider) { Volume = 0.5f };
                                var echoDelay = new OffsetSampleProvider(echoVol) { DelayBy = TimeSpan.FromMilliseconds(s * stepDurationMs + 200) };
                                mixer.AddMixerInput(echoDelay);
                            }
                        }
                    }
                }

                if (disposables.Count > 0)
                {
                    MediaFoundationEncoder.EncodeToMp3(mixer.ToWaveProvider(), outputPath);
                    TxtStatus.Text = "MP3 Exported!";
                }
            }
            catch
            {
                TxtStatus.Text = "Export failed.";
            }
            finally
            {
                foreach (var d in disposables) d.Dispose();
            }
        }
    }
}