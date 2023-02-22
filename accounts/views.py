from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from fido2 import cbor
from fido2.server import Fido2Server
from fido2.webauthn import (
    AttestationObject,
    AuthenticatorData,
    CollectedClientData,
    PublicKeyCredentialRpEntity,
)

from .models import FIDOCredential


if hasattr(settings, 'FIDO2_APP_ID'):
    appId = settings.FIDO2_APP_ID
else:
    appId = "localhost"
rp = PublicKeyCredentialRpEntity(appId, "Ledger Web")
fido_server = Fido2Server(rp)


class LoginView(auth_views.LoginView):
    def post(self, request):
        user = authenticate(request=request, username=request.POST['username'], password=request.POST['password'])
        if user is not None:
            fido_credentials = user.fidocredential_set.count()
            if fido_credentials > 0:
                request.session['user'] = user.id
                return render(
                    request,
                    'registration/login-fido.html',
                    {'form': self.authentication_form},
                )
        return super().post(request)


@login_required
@require_GET
def register_fido(request):
    return render(
        request,
        'registration/register-fido.html',
        {},
    )

@login_required
@require_POST
@csrf_exempt
def register_begin(request):
    registration_data, state = fido_server.register_begin(
        {
            "id": str(request.user.id).encode(),
            "name": request.user.username,
            "displayName": '{} {}'.format(
                request.user.first_name,
                request.user.last_name,
            ),
        },
    )
    request.session["state"] = state
    return HttpResponse(
        cbor.encode(registration_data),
        content_type="application/cbor",
    )

@login_required
@require_POST
@csrf_exempt
def register_complete(request):
    data = cbor.decode(request.body)
    credential_name = data.pop("credentialName", "")
    client_data = CollectedClientData(data["clientDataJSON"])
    att_obj = AttestationObject(data["attestationObject"])
    auth_data = fido_server.register_complete(
        request.session["state"],
        client_data,
        att_obj,
    )
    FIDOCredential.objects.create(
        user=request.user,
        credential=auth_data.credential_data,
        credential_name=credential_name,
    )
    return HttpResponse(
        cbor.encode({"status": "OK"}),
        content_type='application/cbor',
    )


@require_POST
@csrf_exempt
def authenticate_begin(request):
    credentials = [
        row.credential
        for row
        in User.objects.get(pk=request.session['user']).fidocredential_set.all()
    ]
    if len(credentials) == 0:
        raise Http404

    auth_data, state = fido_server.authenticate_begin(credentials)
    request.session["state"] = state
    return HttpResponse(
        cbor.encode(auth_data),
        content_type='application/cbor',
    )

@require_POST
@csrf_exempt
def authenticate_complete(request):
    data = cbor.decode(request.body)
    credential_id = data["credentialId"]
    client_data = CollectedClientData(data["clientDataJSON"])
    auth_data = AuthenticatorData(data["authenticatorData"])
    signature = data["signature"]
    credentials = [
        row.credential
        for row
        in User.objects.get(pk=request.session['user']).fidocredential_set.all()
    ]

    fido_server.authenticate_complete(
        request.session.pop("state"),
        credentials,
        credential_id,
        client_data,
        auth_data,
        signature,
    )

    try:
        user = User.objects.get(pk=request.session.pop('user'))
    except User.DoesNotExist:
        raise Http404
    else:
        # If we're here, we've already confirmed the user has the
        # username and the password.
        login(request, user)

    return HttpResponse(
        cbor.encode({"status": "OK"}),
        content_type='application/cbor',
    )
