# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Individual preference tabs for the preferences dialog."""

from pathlib import Path
from typing import Literal, cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ripstream.core.utils import decode_secret, encode_secret
from ripstream.ui.preferences import BasePreferenceTab


class GeneralTab(BasePreferenceTab):
    """General application settings tab."""

    def setup_ui(self):
        """Instantiate and setup the UI for `GeneralTab`."""
        layout = QVBoxLayout(self)

        # Download Location Group
        location_group = QGroupBox("Download Location")
        location_layout = QFormLayout(location_group)

        location_row = QHBoxLayout()
        self.download_folder = QLineEdit()
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_download_folder)
        location_row.addWidget(self.download_folder)
        location_row.addWidget(self.browse_button)

        location_layout.addRow("Download Folder:", location_row)

        self.source_subdirs = QCheckBox(
            "Create source-specific subfolders (Qobuz, Tidal, etc.)"
        )
        location_layout.addRow(self.source_subdirs)

        self.disc_subdirs = QCheckBox("Create disc subfolders for multi-disc albums")
        location_layout.addRow(self.disc_subdirs)

        layout.addWidget(location_group)

        # Interface Group
        interface_group = QGroupBox("Interface")
        interface_layout = QFormLayout(interface_group)

        self.check_updates = QCheckBox("Check for updates on startup")
        interface_layout.addRow(self.check_updates)

        self.text_output = QCheckBox("Show download status messages")
        interface_layout.addRow(self.text_output)

        self.progress_bars = QCheckBox("Show progress bars")
        interface_layout.addRow(self.progress_bars)

        layout.addWidget(interface_group)

        # File and Folder Naming Group
        naming_group = QGroupBox("File and Folder Naming")
        naming_layout = QFormLayout(naming_group)

        self.folder_format = QLineEdit()
        naming_layout.addRow("Folder Format:", self.folder_format)

        self.track_format = QLineEdit()
        naming_layout.addRow("Track Format:", self.track_format)

        self.add_singles_folder = QCheckBox("Create folders for single tracks")
        naming_layout.addRow(self.add_singles_folder)

        self.restrict_chars = QCheckBox("Restrict to printable ASCII characters")
        naming_layout.addRow(self.restrict_chars)

        self.truncate_length = QSpinBox()
        self.truncate_length.setRange(0, 500)
        self.truncate_length.setSpecialValueText("No Limit")
        naming_layout.addRow("Truncate Filenames To:", self.truncate_length)

        layout.addWidget(naming_group)

        # Metadata Settings Group
        metadata_group = QGroupBox("Metadata")
        metadata_layout = QFormLayout(metadata_group)

        self.playlist_to_album = QCheckBox("Set ALBUM field to playlist name")
        metadata_layout.addRow(self.playlist_to_album)

        self.renumber_playlist = QCheckBox("Renumber playlist tracks")
        metadata_layout.addRow(self.renumber_playlist)

        self.exclude_tags = QLineEdit()
        self.exclude_tags.setPlaceholderText("Comma-separated list of tags to exclude")
        metadata_layout.addRow("Exclude Tags:", self.exclude_tags)

        layout.addWidget(metadata_group)

        layout.addStretch()

    def browse_download_folder(self):
        """Open folder browser for download location."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Download Folder", self.download_folder.text()
        )
        if folder:
            self.download_folder.setText(folder)

    def load_config(self):
        """Load configuration values."""
        self.download_folder.setText(str(self.config.downloads.folder))
        self.source_subdirs.setChecked(self.config.downloads.source_subdirectories)
        self.disc_subdirs.setChecked(self.config.downloads.disc_subdirectories)
        self.check_updates.setChecked(self.config.misc.check_for_updates)
        self.text_output.setChecked(self.config.cli.text_output)
        self.progress_bars.setChecked(self.config.cli.progress_bars)

        # Load file configuration
        self.folder_format.setText(self.config.filepaths.folder_format)
        self.track_format.setText(self.config.filepaths.track_format)
        self.add_singles_folder.setChecked(self.config.filepaths.add_singles_to_folder)
        self.restrict_chars.setChecked(self.config.filepaths.restrict_characters)

        truncate_val = self.config.filepaths.truncate_to
        if isinstance(truncate_val, bool) and not truncate_val:
            self.truncate_length.setValue(0)
        else:
            self.truncate_length.setValue(int(truncate_val))

        self.playlist_to_album.setChecked(self.config.metadata.set_playlist_to_album)
        self.renumber_playlist.setChecked(self.config.metadata.renumber_playlist_tracks)
        self.exclude_tags.setText(", ".join(self.config.metadata.exclude))

    def save_config(self):
        """Save configuration values."""
        # Update download settings
        self.config.downloads.folder = Path(self.download_folder.text())
        self.config.downloads.source_subdirectories = self.source_subdirs.isChecked()
        self.config.downloads.disc_subdirectories = self.disc_subdirs.isChecked()

        # Update interface settings
        self.config.misc.check_for_updates = self.check_updates.isChecked()
        self.config.cli.text_output = self.text_output.isChecked()
        self.config.cli.progress_bars = self.progress_bars.isChecked()

        # Save file configuration
        self.config.filepaths.folder_format = self.folder_format.text()
        self.config.filepaths.track_format = self.track_format.text()
        self.config.filepaths.add_singles_to_folder = (
            self.add_singles_folder.isChecked()
        )
        self.config.filepaths.restrict_characters = self.restrict_chars.isChecked()

        truncate_val = self.truncate_length.value()
        self.config.filepaths.truncate_to = False if truncate_val == 0 else truncate_val

        self.config.metadata.set_playlist_to_album = self.playlist_to_album.isChecked()
        self.config.metadata.renumber_playlist_tracks = (
            self.renumber_playlist.isChecked()
        )

        exclude_text = self.exclude_tags.text().strip()
        if exclude_text:
            self.config.metadata.exclude = [
                tag.strip() for tag in exclude_text.split(",")
            ]
        else:
            self.config.metadata.exclude = []


class ServicesTab(BasePreferenceTab):
    """Service authentication settings tab."""

    def setup_ui(self):
        """Instantiate and setup the UI for `ServicesTab`."""
        # Create scroll area for service settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)

        # Qobuz
        self.qobuz_group = self.create_qobuz_group()
        layout.addWidget(self.qobuz_group)

        # Tidal
        self.tidal_group = self.create_tidal_group()
        layout.addWidget(self.tidal_group)

        # Deezer
        self.deezer_group = self.create_deezer_group()
        layout.addWidget(self.deezer_group)

        # SoundCloud
        self.soundcloud_group = self.create_soundcloud_group()
        layout.addWidget(self.soundcloud_group)

        # YouTube
        self.youtube_group = self.create_youtube_group()
        layout.addWidget(self.youtube_group)

        layout.addStretch()
        scroll.setWidget(content)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(scroll)

    def create_qobuz_group(self):
        """Create Qobuz authentication group."""
        group = QGroupBox("Qobuz")
        layout = QFormLayout(group)

        self.qobuz_email = QLineEdit()
        layout.addRow("Email/User ID:", self.qobuz_email)

        self.qobuz_password = QLineEdit()
        self.qobuz_password.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("Password:", self.qobuz_password)

        self.qobuz_quality = QComboBox()
        self.qobuz_quality.addItems([
            "1 - 320kbps MP3",
            "2 - 16-bit/44.1kHz FLAC",
            "3 - 24-bit/≤96kHz FLAC",
            "4 - 24-bit/≥96kHz FLAC",
        ])
        layout.addRow("Quality:", self.qobuz_quality)

        self.qobuz_booklets = QCheckBox("Download booklet PDFs")
        layout.addRow(self.qobuz_booklets)

        # Add secrets display (read-only)
        secrets_label = QLabel("API Secrets:")
        secrets_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addRow(secrets_label)

        self.qobuz_secrets_list = QTextEdit()
        self.qobuz_secrets_list.setReadOnly(True)
        self.qobuz_secrets_list.setMaximumHeight(80)
        self.qobuz_secrets_list.setPlaceholderText(
            "Secrets will be automatically retrieved when authenticating"
        )
        layout.addRow("", self.qobuz_secrets_list)

        return group

    def create_tidal_group(self):
        """Create Tidal authentication group."""
        group = QGroupBox("Tidal")
        layout = QFormLayout(group)

        self.tidal_token = QLineEdit()
        self.tidal_token.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("Access Token:", self.tidal_token)

        self.tidal_refresh = QLineEdit()
        self.tidal_refresh.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("Refresh Token:", self.tidal_refresh)

        self.tidal_user_id = QLineEdit()
        layout.addRow("User ID:", self.tidal_user_id)

        self.tidal_country = QLineEdit()
        layout.addRow("Country Code:", self.tidal_country)

        self.tidal_quality = QComboBox()
        self.tidal_quality.addItems([
            "0 - 256kbps AAC",
            "1 - 320kbps AAC",
            "2 - 16-bit/44.1kHz FLAC (HiFi)",
            "3 - 24-bit/44.1kHz FLAC (MQA)",
        ])
        layout.addRow("Quality:", self.tidal_quality)

        self.tidal_videos = QCheckBox("Download videos")
        layout.addRow(self.tidal_videos)

        return group

    def create_deezer_group(self):
        """Create Deezer authentication group."""
        group = QGroupBox("Deezer")
        layout = QFormLayout(group)

        self.deezer_arl = QLineEdit()
        self.deezer_arl.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("ARL Cookie:", self.deezer_arl)

        self.deezer_quality = QComboBox()
        self.deezer_quality.addItems(["0 - 128kbps MP3", "1 - 320kbps MP3", "2 - FLAC"])
        layout.addRow("Quality:", self.deezer_quality)

        self.deezer_deezloader = QCheckBox("Use deezloader for free downloads")
        layout.addRow(self.deezer_deezloader)

        return group

    def create_soundcloud_group(self):
        """Create SoundCloud authentication group."""
        group = QGroupBox("SoundCloud")
        layout = QFormLayout(group)

        self.soundcloud_client_id = QLineEdit()
        layout.addRow("Client ID:", self.soundcloud_client_id)

        self.soundcloud_app_version = QLineEdit()
        layout.addRow("App Version:", self.soundcloud_app_version)

        return group

    def create_youtube_group(self):
        """Create YouTube authentication group."""
        group = QGroupBox("YouTube")
        layout = QFormLayout(group)

        self.youtube_videos = QCheckBox("Download videos along with audio")
        layout.addRow(self.youtube_videos)

        video_path_row = QHBoxLayout()
        self.youtube_video_path = QLineEdit()
        self.youtube_browse = QPushButton("Browse...")
        self.youtube_browse.clicked.connect(self.browse_youtube_folder)
        video_path_row.addWidget(self.youtube_video_path)
        video_path_row.addWidget(self.youtube_browse)

        layout.addRow("Video Download Folder:", video_path_row)

        return group

    def browse_youtube_folder(self):
        """Browse for YouTube video download folder."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select YouTube Video Folder", self.youtube_video_path.text()
        )
        if folder:
            self.youtube_video_path.setText(folder)

    def load_config(self):
        """Load service configurations."""
        # Qobuz
        self.qobuz_email.setText(decode_secret(self.config.qobuz.email_or_userid))
        self.qobuz_password.setText(decode_secret(self.config.qobuz.password_or_token))
        self.qobuz_quality.setCurrentIndex(self.config.qobuz.quality - 1)
        self.qobuz_booklets.setChecked(self.config.qobuz.download_booklets)

        # Display secrets (read-only)
        if self.config.qobuz.secrets:
            secrets_text = "\n".join([
                f"Secret {i + 1}: {secret[:8]}..."
                for i, secret in enumerate(self.config.qobuz.secrets)
            ])
            self.qobuz_secrets_list.setPlainText(secrets_text)
        else:
            self.qobuz_secrets_list.setPlainText(
                "No secrets available - will be retrieved automatically when authenticating"
            )

        # Tidal
        self.tidal_token.setText(decode_secret(self.config.tidal.access_token))
        self.tidal_refresh.setText(decode_secret(self.config.tidal.refresh_token))
        self.tidal_user_id.setText(self.config.tidal.user_id)
        self.tidal_country.setText(self.config.tidal.country_code)
        self.tidal_quality.setCurrentIndex(self.config.tidal.quality)
        self.tidal_videos.setChecked(self.config.tidal.download_videos)

        # Deezer
        self.deezer_arl.setText(decode_secret(self.config.deezer.arl))
        self.deezer_quality.setCurrentIndex(self.config.deezer.quality)
        self.deezer_deezloader.setChecked(self.config.deezer.use_deezloader)

        # SoundCloud
        self.soundcloud_client_id.setText(self.config.soundcloud.client_id)
        self.soundcloud_app_version.setText(self.config.soundcloud.app_version)

        # YouTube
        self.youtube_videos.setChecked(self.config.youtube.download_videos)
        self.youtube_video_path.setText(str(self.config.youtube.video_downloads_folder))

    def save_config(self):
        """Save service configurations with encoded secrets."""
        # Qobuz
        self.config.qobuz.email_or_userid = encode_secret(self.qobuz_email.text())
        self.config.qobuz.password_or_token = encode_secret(self.qobuz_password.text())
        self.config.qobuz.quality = self.qobuz_quality.currentIndex() + 1
        self.config.qobuz.download_booklets = self.qobuz_booklets.isChecked()

        # Tidal
        self.config.tidal.access_token = encode_secret(self.tidal_token.text())
        self.config.tidal.refresh_token = encode_secret(self.tidal_refresh.text())
        self.config.tidal.user_id = self.tidal_user_id.text()
        self.config.tidal.country_code = self.tidal_country.text()
        self.config.tidal.quality = self.tidal_quality.currentIndex()
        self.config.tidal.download_videos = self.tidal_videos.isChecked()

        # Deezer
        self.config.deezer.arl = encode_secret(self.deezer_arl.text())
        self.config.deezer.quality = self.deezer_quality.currentIndex()
        self.config.deezer.use_deezloader = self.deezer_deezloader.isChecked()

        # SoundCloud
        self.config.soundcloud.client_id = self.soundcloud_client_id.text()
        self.config.soundcloud.app_version = self.soundcloud_app_version.text()

        # YouTube
        self.config.youtube.download_videos = self.youtube_videos.isChecked()
        self.config.youtube.video_downloads_folder = Path(
            self.youtube_video_path.text()
        )


class DownloadsTab(BasePreferenceTab):
    """Download behavior settings tab."""

    def setup_ui(self):
        """Instantiate and setup the UI for `DownloadsTab`."""
        layout = QVBoxLayout(self)

        # Connection Settings
        connection_group = QGroupBox("Connection Settings")
        connection_layout = QFormLayout(connection_group)

        self.max_connections = QSpinBox()
        self.max_connections.setRange(-1, 100)
        self.max_connections.setSpecialValueText("No Limit")
        connection_layout.addRow("Max Concurrent Downloads:", self.max_connections)

        self.requests_per_minute = QSpinBox()
        self.requests_per_minute.setRange(-1, 1000)
        self.requests_per_minute.setSpecialValueText("No Limit")
        connection_layout.addRow("API Requests per Minute:", self.requests_per_minute)

        self.verify_ssl = QCheckBox("Verify SSL certificates")
        connection_layout.addRow(self.verify_ssl)

        layout.addWidget(connection_group)

        # Download Behavior
        behavior_group = QGroupBox("Download Behavior")
        behavior_layout = QFormLayout(behavior_group)

        self.concurrent_downloads = QCheckBox("Download tracks concurrently")
        behavior_layout.addRow(self.concurrent_downloads)

        self.probe_audio_technicals = QCheckBox(
            "Probe downloaded files for technical info (slower)"
        )
        behavior_layout.addRow(self.probe_audio_technicals)

        layout.addWidget(behavior_group)

        # Database Settings
        database_group = QGroupBox("Database Settings")
        database_layout = QFormLayout(database_group)

        self.track_downloads = QCheckBox("Track downloaded files to avoid duplicates")
        database_layout.addRow(self.track_downloads)

        db_path_row = QHBoxLayout()
        self.downloads_db_path = QLineEdit()
        self.browse_db_button = QPushButton("Browse...")
        self.browse_db_button.clicked.connect(self.browse_db_path)
        db_path_row.addWidget(self.downloads_db_path)
        db_path_row.addWidget(self.browse_db_button)
        database_layout.addRow("Downloads Database:", db_path_row)

        self.history_limit = QSpinBox()
        self.history_limit.setRange(10, 1000)
        self.history_limit.setSuffix(" items")
        database_layout.addRow("History Display Limit:", self.history_limit)

        # Session snapshot items cap (0 = Unlimited)
        self.session_snapshot_cap = QSpinBox()
        self.session_snapshot_cap.setRange(0, 100000)
        self.session_snapshot_cap.setSpecialValueText("Unlimited")
        self.session_snapshot_cap.setSuffix(" items")
        database_layout.addRow("Session Snapshot Items Cap:", self.session_snapshot_cap)

        layout.addWidget(database_group)
        layout.addStretch()

    def browse_db_path(self):
        """Browse for downloads database path."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Downloads Database Location",
            self.downloads_db_path.text(),
            "Database Files (*.db);;All Files (*)",
        )
        if file_path:
            self.downloads_db_path.setText(file_path)

    def load_config(self):
        """Load download configuration."""
        self.max_connections.setValue(self.config.downloads.max_connections)
        self.requests_per_minute.setValue(self.config.downloads.requests_per_minute)
        self.verify_ssl.setChecked(self.config.downloads.verify_ssl)
        self.concurrent_downloads.setChecked(self.config.downloads.concurrency)
        # Audio technicals probing
        self.probe_audio_technicals.setChecked(
            getattr(self.config.downloads, "probe_audio_technicals", False)
        )

        self.track_downloads.setChecked(self.config.database.downloads_enabled)
        self.downloads_db_path.setText(str(self.config.database.database_path))
        # Keep database history limit aligned with search results preference
        self.history_limit.setValue(self.config.cli.max_search_results)
        # Load snapshot cap from config (0 = unlimited)
        cap_val_raw = getattr(self.config.database, "session_snapshot_items_cap", 1000)
        try:
            cap_val = int(cap_val_raw)
        except (TypeError, ValueError):
            cap_val = 1000
        self.session_snapshot_cap.setValue(cap_val)

    def save_config(self):
        """Save download configuration."""
        self.config.downloads.max_connections = self.max_connections.value()
        self.config.downloads.requests_per_minute = self.requests_per_minute.value()
        self.config.downloads.verify_ssl = self.verify_ssl.isChecked()
        self.config.downloads.concurrency = self.concurrent_downloads.isChecked()
        self.config.downloads.probe_audio_technicals = (
            self.probe_audio_technicals.isChecked()
        )

        self.config.database.downloads_enabled = self.track_downloads.isChecked()
        self.config.database.database_path = Path(self.downloads_db_path.text())
        # Keep both settings in sync
        self.config.cli.max_search_results = self.history_limit.value()
        self.config.database.history_limit = self.history_limit.value()
        # Save session snapshot cap
        self.config.database.session_snapshot_items_cap = int(
            self.session_snapshot_cap.value()
        )


class AudioTab(BasePreferenceTab):
    """Audio conversion and artwork settings tab."""

    def setup_ui(self):
        """Instantiate and setup the UI for `AudioTab`."""
        layout = QVBoxLayout(self)

        # Conversion Settings
        conversion_group = QGroupBox("Audio Conversion")
        conversion_layout = QFormLayout(conversion_group)

        self.enable_conversion = QCheckBox("Convert audio after download")
        conversion_layout.addRow(self.enable_conversion)

        self.codec = QComboBox()
        self.codec.addItems(["FLAC", "ALAC", "OPUS", "MP3", "VORBIS", "AAC"])
        conversion_layout.addRow("Target Codec:", self.codec)

        self.sampling_rate = QSpinBox()
        self.sampling_rate.setRange(8000, 192000)
        self.sampling_rate.setSuffix(" Hz")
        conversion_layout.addRow("Sampling Rate:", self.sampling_rate)

        self.bit_depth = QComboBox()
        self.bit_depth.addItems(["16", "24"])
        conversion_layout.addRow("Bit Depth:", self.bit_depth)

        self.lossy_bitrate = QSpinBox()
        self.lossy_bitrate.setRange(64, 320)
        self.lossy_bitrate.setSuffix(" kbps")
        conversion_layout.addRow("Lossy Bitrate:", self.lossy_bitrate)

        layout.addWidget(conversion_group)

        # Artwork Settings
        artwork_group = QGroupBox("Artwork")
        artwork_layout = QFormLayout(artwork_group)

        self.embed_artwork = QCheckBox("Embed artwork in audio files")
        artwork_layout.addRow(self.embed_artwork)

        self.embed_size = QComboBox()
        self.embed_size.addItems(["thumbnail", "small", "large", "original"])
        artwork_layout.addRow("Embedded Size:", self.embed_size)

        self.embed_max_width = QSpinBox()
        self.embed_max_width.setRange(-1, 10000)
        self.embed_max_width.setSpecialValueText("No Limit")
        self.embed_max_width.setSuffix(" px")
        artwork_layout.addRow("Embedded Max Width:", self.embed_max_width)

        self.save_artwork = QCheckBox("Save artwork as separate file")
        artwork_layout.addRow(self.save_artwork)

        self.saved_max_width = QSpinBox()
        self.saved_max_width.setRange(-1, 10000)
        self.saved_max_width.setSpecialValueText("No Limit")
        self.saved_max_width.setSuffix(" px")
        artwork_layout.addRow("Saved Max Width:", self.saved_max_width)

        layout.addWidget(artwork_group)
        layout.addStretch()

    def load_config(self):
        """Load audio configuration."""
        # Conversion
        self.enable_conversion.setChecked(self.config.conversion.enabled)
        codec_index = self.codec.findText(self.config.conversion.codec)
        if codec_index >= 0:
            self.codec.setCurrentIndex(codec_index)
        self.sampling_rate.setValue(self.config.conversion.sampling_rate)
        self.bit_depth.setCurrentText(str(self.config.conversion.bit_depth))
        self.lossy_bitrate.setValue(self.config.conversion.lossy_bitrate)

        # Artwork
        self.embed_artwork.setChecked(self.config.artwork.embed)
        size_index = self.embed_size.findText(self.config.artwork.embed_size)
        if size_index >= 0:
            self.embed_size.setCurrentIndex(size_index)
        self.embed_max_width.setValue(self.config.artwork.embed_max_width)
        self.save_artwork.setChecked(self.config.artwork.save_artwork)
        self.saved_max_width.setValue(self.config.artwork.saved_max_width)

    def save_config(self):
        """Save audio configuration."""
        self._save_conversion_config()
        self._save_artwork_config()

    def _save_conversion_config(self):
        """Save conversion configuration settings."""
        self.config.conversion.enabled = self.enable_conversion.isChecked()

        # Map codec text to codec value with proper typing
        codec_text = self.codec.currentText()
        if codec_text in ["FLAC", "ALAC", "OPUS", "MP3", "VORBIS", "AAC"]:
            self.config.conversion.codec = cast(
                'Literal["FLAC", "ALAC", "OPUS", "MP3", "VORBIS", "AAC"]', codec_text
            )

        self.config.conversion.sampling_rate = self.sampling_rate.value()

        # Map bit depth text to integer value with proper typing
        bit_depth_text = self.bit_depth.currentText()
        if bit_depth_text == "16":
            self.config.conversion.bit_depth = cast("Literal[16, 24]", 16)
        elif bit_depth_text == "24":
            self.config.conversion.bit_depth = cast("Literal[16, 24]", 24)

        self.config.conversion.lossy_bitrate = self.lossy_bitrate.value()

    def _save_artwork_config(self):
        """Save artwork configuration settings."""
        self.config.artwork.embed = self.embed_artwork.isChecked()

        # Map embed size text to size value with proper typing
        embed_size_text = self.embed_size.currentText()
        if embed_size_text in ["thumbnail", "small", "large", "original"]:
            self.config.artwork.embed_size = cast(
                "Literal['thumbnail', 'small', 'large', 'original']", embed_size_text
            )

        self.config.artwork.embed_max_width = self.embed_max_width.value()
        self.config.artwork.save_artwork = self.save_artwork.isChecked()
        self.config.artwork.saved_max_width = self.saved_max_width.value()


class AdvancedTab(BasePreferenceTab):
    """Advanced settings tab."""

    def setup_ui(self):
        """Instantiate and setup the UI for `AdvancedTab`."""
        layout = QVBoxLayout(self)

        # Qobuz Filters
        qobuz_group = QGroupBox("Qobuz Discography Filters")
        qobuz_layout = QFormLayout(qobuz_group)

        self.filter_extras = QCheckBox(
            "Remove collector editions, live recordings, etc."
        )
        qobuz_layout.addRow(self.filter_extras)

        self.filter_repeats = QCheckBox("Pick highest quality from identical titles")
        qobuz_layout.addRow(self.filter_repeats)

        self.filter_non_albums = QCheckBox("Remove EPs and singles")
        qobuz_layout.addRow(self.filter_non_albums)

        self.filter_features = QCheckBox("Remove albums where artist is not main")
        qobuz_layout.addRow(self.filter_features)

        self.filter_non_studio = QCheckBox("Skip non-studio albums")
        qobuz_layout.addRow(self.filter_non_studio)

        self.filter_non_remaster = QCheckBox("Only download remastered albums")
        qobuz_layout.addRow(self.filter_non_remaster)

        layout.addWidget(qobuz_group)

        # Last.fm Settings
        lastfm_group = QGroupBox("Last.fm Integration")
        lastfm_layout = QFormLayout(lastfm_group)

        self.lastfm_source = QComboBox()
        self.lastfm_source.addItems([
            "qobuz",
            "tidal",
            "deezer",
            "soundcloud",
            "youtube",
        ])
        lastfm_layout.addRow("Primary Source:", self.lastfm_source)

        self.lastfm_fallback = QComboBox()
        self.lastfm_fallback.addItems([
            "",
            "qobuz",
            "tidal",
            "deezer",
            "soundcloud",
            "youtube",
        ])
        lastfm_layout.addRow("Fallback Source:", self.lastfm_fallback)

        layout.addWidget(lastfm_group)

        # Search Settings
        cli_group = QGroupBox("Search Settings")
        cli_layout = QFormLayout(cli_group)

        self.max_search_results = QSpinBox()
        self.max_search_results.setRange(1, 1000)
        cli_layout.addRow("Max Search Results:", self.max_search_results)

        layout.addWidget(cli_group)
        layout.addStretch()

    def load_config(self):
        """Load advanced configuration."""
        # Qobuz filters
        self.filter_extras.setChecked(self.config.qobuz_filters.extras)
        self.filter_repeats.setChecked(self.config.qobuz_filters.repeats)
        self.filter_non_albums.setChecked(self.config.qobuz_filters.non_albums)
        self.filter_features.setChecked(self.config.qobuz_filters.features)
        self.filter_non_studio.setChecked(self.config.qobuz_filters.non_studio_albums)
        self.filter_non_remaster.setChecked(self.config.qobuz_filters.non_remaster)

        # Last.fm
        source_index = self.lastfm_source.findText(self.config.lastfm.source)
        if source_index >= 0:
            self.lastfm_source.setCurrentIndex(source_index)

        fallback_index = self.lastfm_fallback.findText(
            self.config.lastfm.fallback_source
        )
        if fallback_index >= 0:
            self.lastfm_fallback.setCurrentIndex(fallback_index)

        # Search
        self.max_search_results.setValue(self.config.cli.max_search_results)

    def save_config(self):
        """Save advanced configuration."""
        # Qobuz filters
        self.config.qobuz_filters.extras = self.filter_extras.isChecked()
        self.config.qobuz_filters.repeats = self.filter_repeats.isChecked()
        self.config.qobuz_filters.non_albums = self.filter_non_albums.isChecked()
        self.config.qobuz_filters.features = self.filter_features.isChecked()
        self.config.qobuz_filters.non_studio_albums = self.filter_non_studio.isChecked()
        self.config.qobuz_filters.non_remaster = self.filter_non_remaster.isChecked()

        # Last.fm
        self.config.lastfm.source = self.lastfm_source.currentText()
        self.config.lastfm.fallback_source = self.lastfm_fallback.currentText()

        # Search
        self.config.cli.max_search_results = self.max_search_results.value()
        # Keep database history limit in sync with search preference
        self.config.database.history_limit = self.config.cli.max_search_results
