"""Sprint 9: single source of truth for the app's own version display (About
dialog). packaging/memoryos.iss's #define MyAppVersion is a separate,
manually-synced hardcoded value -- Inno Setup's preprocessor can't import a
Python constant, and a shared build-time mechanism isn't worth the added
complexity for one two-place string at this project's scale. Keep both in
sync by hand on every version bump."""

__version__ = "1.1.0"
