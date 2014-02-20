import unittest
import common
import hashlib

from trezorlib import messages_pb2 as proto
from mnemonic import Mnemonic

def generate_entropy(strength, internal_entropy, external_entropy):
    '''
    strength - length of produced seed. One of 128, 192, 256
    random - binary stream of random data from external HRNG
    '''
    if strength not in (128, 192, 256):
        raise Exception("Invalid strength")

    if not internal_entropy:
        raise Exception("Internal entropy is not provided")

    if len(internal_entropy) < 32:
        raise Exception("Internal entropy too short")

    if not external_entropy:
        raise Exception("External entropy is not provided")

    if len(external_entropy) < 32:
        raise Exception("External entropy too short")

    entropy = hashlib.sha256(internal_entropy + external_entropy).digest()
    entropy_stripped = entropy[:strength / 8]

    if len(entropy_stripped) * 8 != strength:
        raise Exception("Entropy length mismatch")

    return entropy_stripped

class TestDeviceReset(common.TrezorTest):

    def test_reset_device(self):
        # No PIN, no passphrase
        external_entropy = 'zlutoucky kun upel divoke ody' * 2
        strength = 128

        ret = self.client.call_raw(proto.ResetDevice(display_random=False,
                                               strength=strength,
                                               passphrase_protection=False,
                                               pin_protection=False,
                                               language='english',
                                               label='test'))

        self.assertIsInstance(ret, proto.ButtonRequest)
        self.client.debug.press_yes()
        ret = self.client.call_raw(proto.ButtonAck())

        self.assertIsInstance(ret, proto.EntropyRequest)
        ret = self.client.call_raw(proto.EntropyAck(entropy=external_entropy))

        # Read internal entropy and generate mnemonic locally
        internal_entropy = self.client.debug.read_entropy()
        entropy = generate_entropy(strength, internal_entropy, external_entropy)
        expected_mnemonic = Mnemonic('english').to_mnemonic(entropy)

        mnemonic = []
        for _ in range(12):
            self.assertIsInstance(ret, proto.ButtonRequest)
            mnemonic.append(self.client.debug.read_word()[0])
            self.client.debug.press_yes()
            self.client.call_raw(proto.ButtonAck())

        mnemonic = ' '.join(mnemonic)

        # Compare that device generated proper mnemonic for given entropies
        self.assertEqual(mnemonic, expected_mnemonic)

        mnemonic = []
        for _ in range(12):
            self.assertIsInstance(ret, proto.ButtonRequest)
            mnemonic.append(self.client.debug.read_word()[0])
            self.client.debug.press_yes()
            resp = self.client.call_raw(proto.ButtonAck())

        self.assertIsInstance(resp, proto.Success)

        mnemonic = ' '.join(mnemonic)

        # Compare that second pass printed out the same mnemonic once again
        self.assertEqual(mnemonic, expected_mnemonic)
        
        # Check if device is properly initialized
        resp = self.client.call_raw(proto.Initialize())
        self.assertFalse(resp.pin_protection)
        self.assertFalse(resp.passphrase_protection)

        # Do passphrase-protected action, PassphraseRequest should NOT be raised
        resp = self.client.call_raw(proto.Ping(passphrase_protection=True))
        self.assertIsInstance(resp, proto.Success)

        # Do PIN-protected action, PinRequest should NOT be raised
        resp = self.client.call_raw(proto.Ping(pin_protection=True))
        self.assertIsInstance(resp, proto.Success)

    def test_reset_device_pin(self):
        external_entropy = 'zlutoucky kun upel divoke ody' * 2
        strength = 128

        ret = self.client.call_raw(proto.ResetDevice(display_random=True,
                                               strength=strength,
                                               passphrase_protection=True,
                                               pin_protection=True,
                                               language='english',
                                               label='test'))

        self.assertIsInstance(ret, proto.ButtonRequest)
        self.client.debug.press_yes()
        ret = self.client.call_raw(proto.ButtonAck())

        self.assertIsInstance(ret, proto.EntropyRequest)
        ret = self.client.call_raw(proto.EntropyAck(entropy=external_entropy))

        self.assertIsInstance(ret, proto.PinMatrixRequest)

        # Enter PIN for first time
        pin_encoded = self.client.debug.encode_pin('654')
        ret = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))
        self.assertIsInstance(ret, proto.PinMatrixRequest)

        # Enter PIN for second time
        pin_encoded = self.client.debug.encode_pin('654')
        ret = self.client.call_raw(proto.PinMatrixAck(pin=pin_encoded))

        # Read internal entropy and generate mnemonic locally
        internal_entropy = self.client.debug.read_entropy()
        entropy = generate_entropy(strength, internal_entropy, external_entropy)
        expected_mnemonic = Mnemonic('english').to_mnemonic(entropy)

        mnemonic = []
        for _ in range(12):
            self.assertIsInstance(ret, proto.ButtonRequest)
            mnemonic.append(self.client.debug.read_word()[0])
            self.client.debug.press_yes()
            self.client.call_raw(proto.ButtonAck())

        mnemonic = ' '.join(mnemonic)

        # Compare that device generated proper mnemonic for given entropies
        self.assertEqual(mnemonic, expected_mnemonic)

        mnemonic = []
        for _ in range(12):
            self.assertIsInstance(ret, proto.ButtonRequest)
            mnemonic.append(self.client.debug.read_word()[0])
            self.client.debug.press_yes()
            resp = self.client.call_raw(proto.ButtonAck())

        self.assertIsInstance(resp, proto.Success)

        mnemonic = ' '.join(mnemonic)

        # Compare that second pass printed out the same mnemonic once again
        self.assertEqual(mnemonic, expected_mnemonic)

        # Check if device is properly initialized
        resp = self.client.call_raw(proto.Initialize())
        self.assertTrue(resp.pin_protection)
        self.assertTrue(resp.passphrase_protection)

        # Do passphrase-protected action, PassphraseRequest should be raised
        resp = self.client.call_raw(proto.Ping(passphrase_protection=True))
        self.assertIsInstance(resp, proto.PassphraseRequest)

        # Do PIN-protected action, PinRequest should be raised
        resp = self.client.call_raw(proto.Ping(pin_protection=True))
        self.assertIsInstance(resp, proto.PinMatrixRequest)
        
if __name__ == '__main__':
    unittest.main()
