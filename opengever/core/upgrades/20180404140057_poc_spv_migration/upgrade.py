from ftw.upgrade import UpgradeStep


class POCSPVMigration(UpgradeStep):
    """POC SPV migration.
    """

    def __call__(self):
        self.install_upgrade_profile()
