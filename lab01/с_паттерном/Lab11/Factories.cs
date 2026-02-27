using Lab11;

namespace DawStudio
{
    public interface IKitFactory
    {
        DrumKit CreateKit();
    }

    public class RockKitFactory : IKitFactory
    {
        public DrumKit CreateKit() => new RockKit();
    }

    public class TrapKitFactory : IKitFactory
    {
        public DrumKit CreateKit() => new TrapKit();
    }

    public class SynthwaveKitFactory : IKitFactory
    {
        public DrumKit CreateKit() => new SynthwaveKit();
    }
}