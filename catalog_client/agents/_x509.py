from OpenSSL.crypto import FILETYPE_PEM, load_certificate

from pyasn1.type import univ, constraint, char, namedtype, tag

from pyasn1.codec.der.decoder import decode

MAX = 64

class DirectoryString(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType(
            'teletexString', char.TeletexString().subtype(
                subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
        namedtype.NamedType(
            'printableString', char.PrintableString().subtype(
                subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
        namedtype.NamedType(
            'universalString', char.UniversalString().subtype(
                subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
        namedtype.NamedType(
            'utf8String', char.UTF8String().subtype(
                subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
        namedtype.NamedType(
            'bmpString', char.BMPString().subtype(
                subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
        namedtype.NamedType(
            'ia5String', char.IA5String().subtype(
                subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
        )


class AttributeValue(DirectoryString):
    pass


class AttributeType(univ.ObjectIdentifier):
    pass


class AttributeTypeAndValue(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('type', AttributeType()),
        namedtype.NamedType('value', AttributeValue()),
        )


class RelativeDistinguishedName(univ.SetOf):
    componentType = AttributeTypeAndValue()

class RDNSequence(univ.SequenceOf):
    componentType = RelativeDistinguishedName()


class Name(univ.Choice):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('', RDNSequence()),
        )


class Extension(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('extnID', univ.ObjectIdentifier()),
        namedtype.DefaultedNamedType('critical', univ.Boolean('False')),
        namedtype.NamedType('extnValue', univ.OctetString()),
        )


class Extensions(univ.SequenceOf):
    componentType = Extension()
    sizeSpec = univ.SequenceOf.sizeSpec + constraint.ValueSizeConstraint(1, MAX)


class GeneralName(univ.Choice):
    componentType = namedtype.NamedTypes(
        # namedtype.NamedType('otherName', AnotherName()),
        namedtype.NamedType('rfc822Name', char.IA5String().subtype(
            implicitTag=tag.Tag(tag.tagClassContext,
                                tag.tagFormatSimple, 1))),
        namedtype.NamedType('dNSName', char.IA5String().subtype(
            implicitTag=tag.Tag(tag.tagClassContext,
                                tag.tagFormatSimple, 2))),
        # namedtype.NamedType('x400Address', ORAddress()),
        namedtype.NamedType('directoryName', Name()),
        # namedtype.NamedType('ediPartyName', EDIPartyName()),
        namedtype.NamedType('uniformResourceIdentifier', char.IA5String()),
        namedtype.NamedType('iPAddress', univ.OctetString()),
        namedtype.NamedType('registeredID', univ.ObjectIdentifier()),
        )


class GeneralNames(univ.SequenceOf):
    componentType = GeneralName()
    sizeSpec = univ.SequenceOf.sizeSpec + constraint.ValueSizeConstraint(1, MAX)


class SubjectAltName(GeneralNames):
    pass


def get_dns_subject_alt_name(filename):
    cert = load_certificate(FILETYPE_PEM, open(filename).read())
    for i in range(cert.get_extension_count()):
        ext = cert.get_extension(i)
        ext = decode(ext.get_data(), asn1Spec=SubjectAltName())
        return ext[0].getComponentByPosition(1).getComponentByPosition(1).asOctets()
