import unittest
from types import SimpleNamespace

from utils.ticket_permissions import get_staff_roles, is_staff_member


def permissions(**overrides):
    defaults = {
        "administrator": False,
        "manage_guild": False,
        "manage_channels": False,
        "manage_messages": False,
        "manage_threads": False,
        "moderate_members": False,
        "kick_members": False,
        "ban_members": False,
        "view_audit_log": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TicketPermissionTests(unittest.TestCase):
    def test_staff_roles_are_discovered_by_permissions_not_only_names(self):
        moderator = SimpleNamespace(name="Community Moderator", permissions=permissions(kick_members=True))
        admin = SimpleNamespace(name="Operations", permissions=permissions(manage_guild=True))
        ordinary = SimpleNamespace(name="Member", permissions=permissions())
        guild = SimpleNamespace(roles=[moderator, admin, ordinary])

        self.assertEqual(get_staff_roles(guild), [moderator, admin])

    def test_legacy_staff_names_remain_supported(self):
        legacy = SimpleNamespace(name="Мэр", permissions=permissions())
        guild = SimpleNamespace(roles=[legacy])
        self.assertEqual(get_staff_roles(guild), [legacy])

    def test_member_is_staff_when_effective_permissions_allow_moderation(self):
        member = SimpleNamespace(
            guild_permissions=permissions(moderate_members=True),
            roles=[],
        )
        self.assertTrue(is_staff_member(member))

    def test_member_is_staff_when_assigned_a_staff_role(self):
        role = SimpleNamespace(name="Moderator", permissions=permissions(manage_messages=True))
        member = SimpleNamespace(guild_permissions=permissions(), roles=[role])
        self.assertTrue(is_staff_member(member))

    def test_regular_member_is_not_staff(self):
        member = SimpleNamespace(guild_permissions=permissions(), roles=[])
        self.assertFalse(is_staff_member(member))
        self.assertFalse(is_staff_member(None))


if __name__ == "__main__":
    unittest.main()
