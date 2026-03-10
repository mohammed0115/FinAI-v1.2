from django.db.models import Q
from rest_framework import permissions, viewsets


class BaseAuthenticatedModelViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_base_queryset(self):
        queryset = getattr(self, 'queryset', None)
        if queryset is None:
            raise AssertionError(f'{self.__class__.__name__} must define queryset.')
        return queryset.all()


class BaseAuthenticatedReadOnlyModelViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_base_queryset(self):
        queryset = getattr(self, 'queryset', None)
        if queryset is None:
            raise AssertionError(f'{self.__class__.__name__} must define queryset.')
        return queryset.all()


class OrganizationScopedQuerysetMixin:
    organization_filter_field = 'organization'
    admin_sees_all = True

    def get_global_access_filter(self):
        return None

    def get_queryset(self):
        queryset = self.get_base_queryset()
        user = self.request.user

        if self.admin_sees_all and getattr(user, 'role', None) == 'admin':
            return queryset

        organization = getattr(user, 'organization', None)
        if organization is None:
            return queryset.none()

        tenant_filter = Q(**{self.organization_filter_field: organization})
        global_filter = self.get_global_access_filter()
        if global_filter is not None:
            return queryset.filter(tenant_filter | global_filter)
        return queryset.filter(tenant_filter)


class OrganizationScopedModelViewSet(OrganizationScopedQuerysetMixin, BaseAuthenticatedModelViewSet):
    organization_save_field = 'organization'
    actor_save_field = None
    update_actor_save_field = None

    def _supports_field(self, field_name):
        if not field_name:
            return False
        model = self.get_base_queryset().model
        return any(field.name == field_name for field in model._meta.get_fields())

    def get_write_organization(self):
        if not self.organization_save_field:
            return None

        user = self.request.user
        explicit_org = self.request.data.get(self.organization_save_field)
        if getattr(user, 'role', None) == 'admin' and explicit_org:
            return None
        return getattr(user, 'organization', None)

    def get_serializer(self, *args, **kwargs):
        incoming = kwargs.get('data')
        if incoming is not None and self._supports_field(self.organization_save_field):
            organization = self.get_write_organization()
            has_org_value = getattr(incoming, 'get', lambda key, default=None: default)(self.organization_save_field)
            if organization is not None and not has_org_value:
                incoming = incoming.copy()
                incoming[self.organization_save_field] = str(organization.pk)
                kwargs['data'] = incoming
        return super().get_serializer(*args, **kwargs)

    def perform_create(self, serializer):
        save_kwargs = {}
        if self._supports_field(self.organization_save_field):
            organization = self.get_write_organization()
            if organization is not None:
                save_kwargs[self.organization_save_field] = organization
        if self._supports_field(self.actor_save_field):
            save_kwargs[self.actor_save_field] = self.request.user
        serializer.save(**save_kwargs)

    def perform_update(self, serializer):
        save_kwargs = {}
        if self._supports_field(self.update_actor_save_field):
            save_kwargs[self.update_actor_save_field] = self.request.user
        serializer.save(**save_kwargs)


class OrganizationScopedReadOnlyModelViewSet(OrganizationScopedQuerysetMixin, BaseAuthenticatedReadOnlyModelViewSet):
    pass
