# Copyright (c) 2015 Ansible, Inc.
# All Rights Reserved
import sys
from distutils.util import strtobool

from django.core.management.base import BaseCommand
from awx.main.models import CredentialType, Credential, Organization


class Command(BaseCommand):
    """Create or update a credential for galaxy/container registry"""

    help = 'Creates or updates a credential for galaxy/container registry.'
    output_transaction = True

    def add_arguments(self, parser):
        parser.add_argument(
            "--name",
            type=str,
            required=True,
            help="Credential Name",
        )
        parser.add_argument(
            "--description",
            type=str,
            help="Credential Description",
        )
        parser.add_argument(
            "--organization",
            type=str,
            help="Organization name to associate credential with",
        )
        parser.add_argument(
            "--credential-type",
            type=str,
            required=True,
            help="Type of credential to create",
        )
        parser.add_argument(
            "--server-url",
            type=str,
            help="Server URL",
        )
        parser.add_argument(
            "--auth-server-url",
            type=str,
            help="Auth Server URL",
        )
        parser.add_argument(
            "--username",
            type=str,
            help="Username for authentication",
        )
        parser.add_argument(
            "--password",
            type=str,
            help="Password or token for authentication",
        )
        parser.add_argument(
            "--verify-ssl",
            type=lambda x: bool(strtobool(str(x))),
            default=True,
            help="Verify SSL when authenticating with the container registry",
        )

    def check_required_fields(self, credential_type, options, required_fields):
        for field in required_fields:
            if not options.get(field):
                sys.stderr.write("'%s' must be provided when creating '%s' credential type.\n" % (field, credential_type))
                sys.exit(1)

    def handle(self, *args, **options):
        changed = False
        credential_type = options.get("credential_type")

        cred_type = CredentialType.objects.filter(kind=credential_type)
        if not cred_type.exists():
            sys.stderr.write("'%s' credential type not found" % credential_type)
            sys.exit(1)

        if credential_type == 'galaxy':
            self.check_required_fields(credential_type, options, ['organization', 'server_url'])
            inputs = {
                "url": options.get("server_url"),
                "auth_url": options.get("auth_server_url"),
                "token": options.get("password"),
            }
        elif credential_type == 'registry':
            self.check_required_fields(credential_type, options, ['server_url'])
            inputs = {
                "host": options.get("server_url"),
                "password": options.get("password"),
                "username": options.get("username"),
                "verify_ssl": options.get("verify_ssl"),
            }
        else:
            sys.stderr.write("Creating '%s' credential type currently not supported" % credential_type)
            sys.exit(1)

        default_values = {'inputs': {k: v for k, v in inputs.items() if v != None}}

        if options.get("description"):
            default_values['description'] = options.get("description")

        org_name = options.get("organization")
        if org_name:
            org = Organization.objects.filter(name=org_name)
            if not org.exists():
                sys.stderr.write("'%s' organization does not exist.\n" % org_name)
                sys.exit(1)
            default_values['organization'] = Organization.objects.get(name=org_name)

        new_cred, cred_created = Credential.objects.get_or_create(
            name=options.get("name"),
            credential_type=cred_type[0],
            defaults=default_values,
        )

        if cred_created:
            changed = True
            print("Created '%s' credential." % options.get("name"))
        else:
            # TODO: add organization/description update

            cred_updated = False
            for key, value in inputs.items():
                if (not new_cred.inputs.get(key) or not new_cred.get_input(key)) and not value:
                    # skip if existing obj and new value are both empty/None
                    continue
                elif new_cred.inputs.get(key) and new_cred.get_input(key) == value:
                    # skip if existing obj and new value are same
                    continue
                else:
                    new_cred.inputs[key] = value
                    cred_updated = True

            if cred_updated:
                new_cred.save()
                changed = True
                print("Updated '%s' credential." % options.get("name"))

        if changed:
            print("(changed: True)")
        else:
            print("(changed: False)")
