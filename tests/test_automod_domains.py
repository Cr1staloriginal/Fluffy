import unittest

from cogs.automod import domain_matches, is_allowed_domain, is_gif_url, is_scam_domain


class AutoModDomainTests(unittest.TestCase):
    def setUp(self):
        self.allowed = {
            "discord.com",
            "discord.gg",
            "cdn.discordapp.com",
            "media.discordapp.net",
            "images-ext-1.discordapp.net",
            "tenor.com",
            "giphy.com",
        }

    def test_official_discord_media_hosts_are_allowed(self):
        for host in (
            "cdn.discordapp.com",
            "media.discordapp.net",
            "images-ext-1.discordapp.net",
            "cdn.discordapp.com.evil.example",
        ):
            if host.endswith(".evil.example"):
                self.assertFalse(is_allowed_domain(host, self.allowed))
            else:
                self.assertTrue(is_allowed_domain(host, self.allowed), host)

    def test_gif_providers_are_allowed(self):
        self.assertTrue(is_allowed_domain("tenor.com", self.allowed))
        self.assertTrue(is_allowed_domain("media.tenor.com", self.allowed))
        self.assertTrue(is_allowed_domain("giphy.com", self.allowed))
        self.assertTrue(is_allowed_domain("i.giphy.com", self.allowed))

    def test_lookalike_domains_are_not_allowed(self):
        self.assertFalse(is_allowed_domain("notdiscordapp.com", self.allowed))
        self.assertFalse(is_allowed_domain("discordapp.com.evil.test", self.allowed))
        self.assertFalse(is_allowed_domain("cdn-discordapp.com", self.allowed))

    def test_blocked_domains_keep_priority(self):
        blocked = {"tinyurl.com"}
        self.assertTrue(is_scam_domain("tinyurl.com", blocked))
        self.assertTrue(is_scam_domain("go.tinyurl.com", blocked))
        self.assertFalse(is_scam_domain("cdn.discordapp.com", blocked))

    def test_direct_gif_files_are_allowed_from_any_host(self):
        self.assertTrue(is_gif_url("https://unknown.example/funny.gif"))
        self.assertTrue(is_gif_url("https://cdn.example/path/ANIMATION.GIF?width=500"))
        self.assertFalse(is_gif_url("https://unknown.example/funny.png"))
        self.assertFalse(is_gif_url("https://unknown.example/gallery?file=funny.gif"))

    def test_path_entries_are_not_mistaken_for_hostnames(self):
        self.assertFalse(domain_matches("discordapp.com", "discordapp.com/gift"))


if __name__ == "__main__":
    unittest.main()
