import frappe
from frappe.model.document import Document
from frappe.model.meta import Meta


class DynamicVirtualDoctype(Document):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_virtual = self.check_if_virtual()

    def check_if_virtual(self):
        # Implement your logic to determine if the doctype should be virtual
        settings = frappe.get_single("TV Data Settings")
        return settings.use_influxdb

    @classmethod
    def get_meta(cls):
        meta = super().get_meta()
        if cls.check_if_virtual(cls):
            meta.is_virtual = 1
        return meta


def set_doctype_virtual(doctype_name, is_virtual):
    """
    Dynamically set a doctype as virtual or non-virtual
    """
    meta = frappe.get_meta(doctype_name)
    meta.is_virtual = 1 if is_virtual else 0
    meta.db_update()

    # Clear cache to ensure changes take effect
    frappe.clear_cache(doctype=doctype_name)


# Monkey patch the Meta class to allow dynamic virtual setting
original_init = Meta.__init__


def patched_init(self, *args, **kwargs):
    original_init(self, *args, **kwargs)
    if hasattr(self, "is_virtual"):
        doctype_class = frappe.get_attr(
            f"{self.module}.doctype.{frappe.scrub(self.name)}.{frappe.scrub(self.name)}.{self.name}"
        )
        if issubclass(doctype_class, DynamicVirtualDoctype):
            self.is_virtual = doctype_class.check_if_virtual()


Meta.__init__ = patched_init

# Apply the patch when this module is imported
frappe.patches.add_patch("dynamic_virtual_doctype", __name__)
