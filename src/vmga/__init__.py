"""VMGA (Vesta Mail Governance Adapter) - Gmail-specific governance extension.

This package provides email-domain-specific policy enforcement for agent runtimes,
building on the core Vesta Agent Runtime Governance framework.
"""

from .vmga_adapter import (
    VMGAGmailAdapter,
    VMGAPolicy,
    VMGAProposal,
    GmailAction,
    ActionClass,
    ContentRisk,
    load_vmga_policy,
)

__all__ = [
    "VMGAGmailAdapter",
    "VMGAPolicy", 
    "VMGAProposal",
    "GmailAction",
    "ActionClass",
    "ContentRisk",
    "load_vmga_policy",
]

__version__ = "0.2.0"
