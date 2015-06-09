import blivet.formats.luks as luks

from tests import loopbackedtestcase

class LUKSTestCase(loopbackedtestcase.LoopBackedTestCase):

    def __init__(self, methodName='runTest'):
        super(LUKSTestCase, self).__init__(methodName=methodName, deviceSpec=[self.DEFAULT_STORE_SIZE])
        self.fmt = luks.LUKS(passphrase="passphrase", name="super-luks")

    def testSimple(self):
        """ Simple test of creation, setup, and teardown. """
        # test that creation of format on device occurs w/out error
        device = self.loopDevices[0]

        self.assertFalse(self.fmt.exists)
        self.fmt.device = device
        self.assertIsNone(self.fmt.create())
        self.assertIsNotNone(self.fmt.mapName)
        self.assertTrue(self.fmt.exists)
        self.assertTrue("LUKS" in self.fmt.name)

        # test that the device can be opened once created
        self.assertIsNone(self.fmt.setup())
        self.assertTrue(self.fmt.status)

        # test that the device can be closed again
        self.assertIsNone(self.fmt.teardown())
        self.assertFalse(self.fmt.status)
