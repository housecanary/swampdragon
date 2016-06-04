import django
from django.db.models.fields.related import ReverseSingleRelatedObjectDescriptor, SingleRelatedObjectDescriptor, \
    ForeignRelatedObjectsDescriptor, ManyRelatedObjectsDescriptor, ReverseManyRelatedObjectsDescriptor


DJANGO_VERSION_BEFORE_1_8 = django.VERSION[:2] < (1, 8)


def _construct_graph(parent_type, child_type, via, is_collection, property_name):
    return {
        'parent_type': parent_type,
        'child_type': child_type,
        'via': via,
        'prop_name': property_name,
        'is_collection': is_collection,
    }


def _serializer_is_ignored(serializer, related_serializer, ignore_serializer_pairs):
    if not ignore_serializer_pairs:
        return False
    if (serializer, related_serializer) in ignore_serializer_pairs:
        return True
    return False


def get_object_map(serializer, ignore_serializer_pairs=None):
    """
    Create an object map from the serializer and it's related serializers.

    For each map created, ignore the pair of serializers that are already mapped
    """
    graph = []
    serializer_instance = serializer()
    if ignore_serializer_pairs is None:
        ignore_serializer_pairs = []

    serializers = serializer.get_related_serializers()

    for related_serializer, field_name in serializers:
        if _serializer_is_ignored(serializer, related_serializer, ignore_serializer_pairs):
            continue

        field_type = getattr(serializer_instance.opts.model, field_name)

        if isinstance(field_type, ReverseSingleRelatedObjectDescriptor):
            # fk
            is_collection = False
            if DJANGO_VERSION_BEFORE_1_8:
                model = field_type.field.related.parent_model
                attname = field_type.field.related.var_name
            else:
                model = field_type.field.rel.model
                attname = field_type.field.rel.name
        elif isinstance(field_type, SingleRelatedObjectDescriptor):
            # o2o
            is_collection = False
            if DJANGO_VERSION_BEFORE_1_8:
                model = field_type.related.model
            else:
                model = field_type.related.related_model
            attname = field_type.related.field.name
        elif isinstance(field_type, ForeignRelatedObjectsDescriptor):
            # reverse fk
            is_collection = True
            if DJANGO_VERSION_BEFORE_1_8:
                model = field_type.related.model
            else:
                model = field_type.related.related_model
            attname = field_type.related.field.get_attname()
        elif isinstance(field_type, ManyRelatedObjectsDescriptor):
            # m2m
            is_collection = True
            if DJANGO_VERSION_BEFORE_1_8:
                model = field_type.related.model
            else:
                model = field_type.related.related_model
            attname = field_type.related.field.name
        elif isinstance(field_type, ReverseManyRelatedObjectsDescriptor):
            # reverse m2m
            is_collection = True
            if DJANGO_VERSION_BEFORE_1_8:
                model = field_type.field.related.parent_model
                attname = field_type.field.related.var_name
            else:
                model = field_type.field.rel.model
                attname = field_type.field.rel.name
        else:
            raise Exception('Unhandled field type: %r' % field_type)

        graph.append(
            _construct_graph(
                parent_type=serializer_instance.opts.model._meta.model_name,
                child_type=model._meta.model_name,
                via=attname,
                is_collection=is_collection,
                property_name=field_name
            )
        )
        ignore_serializer_pairs.append((serializer, related_serializer))
        graph += get_object_map(related_serializer, ignore_serializer_pairs)
    return graph
