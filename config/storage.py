"""Production static storage.  `support_js_module_import_aggregation` makes collectstatic rewrite the relative
`import ... from "./x.js"` inside vendored ES modules (three.js) to their hashed filenames."""
from whitenoise.storage import CompressedManifestStaticFilesStorage


class HashedModuleStorage(CompressedManifestStaticFilesStorage):
    support_js_module_import_aggregation = True
