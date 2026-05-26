from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject

import uuid
import os

app = FastAPI()

# folder na wygenerowane PDF
GENERATED_DIR = "generated"

os.makedirs(GENERATED_DIR, exist_ok=True)

# udostępnianie plików PDF przez URL
app.mount("/generated", StaticFiles(directory=GENERATED_DIR), name="generated")


class WniosekRequest(BaseModel):
    formularz_P: Dict[str, Any]
    formularz_P1: Dict[str, Any]


@app.get("/")
def root():
    return {"status": "API działa"}


def wypelnij_pdf(szablon_pdf, plik_wynikowy, pola):

    reader = PdfReader(szablon_pdf)

    writer = PdfWriter()

    writer.append(reader)

    page = writer.pages[0]

    # ----------------------------
    # pola tekstowe
    # ----------------------------

    pola_tekstowe = {}

    for nazwa, wartosc in pola.items():

        if not str(wartosc).startswith("/"):

            pola_tekstowe[nazwa] = wartosc

    writer.update_page_form_field_values(
        page,
        pola_tekstowe
    )

    # ----------------------------
    # checkboxy
    # ----------------------------

    for field in writer._root_object["/AcroForm"]["/Fields"]:

        obj = field.get_object()

        name = obj.get("/T")

        if name in pola and str(pola[name]).startswith("/"):

            value = NameObject(pola[name])

            obj.update({
                NameObject("/V"): value,
                NameObject("/AS"): value
            })

            # dzieci checkboxów
            if "/Kids" in obj:

                for kid in obj["/Kids"]:

                    kid_obj = kid.get_object()

                    kid_obj.update({
                        NameObject("/AS"): value
                    })

    writer.set_need_appearances_writer()

    with open(plik_wynikowy, "wb") as f:

        writer.write(f)


@app.post("/generuj-wniosek")
def generuj_wniosek(data: WniosekRequest):

    uid = str(uuid.uuid4())

    output_p = f"{GENERATED_DIR}/FormularzP_{uid}.pdf"

    output_p1 = f"{GENERATED_DIR}/FormularzP1_{uid}.pdf"

    # ----------------------------
    # FORMULARZ P
    # ----------------------------

    pola_p = {

        "wnioskodawca_imie_nazwisko_lub_nazwa":
            data.formularz_P.get("wnioskodawca", ""),

        "wnioskodawca_adres":
            data.formularz_P.get("adres", ""),

        "wnioskodawca_telefon_email":
            data.formularz_P.get("telefon_email", ""),

        "uwagi":
            data.formularz_P.get("uwagi", ""),

        # checkboxy
        "material_mapa_zasadnicza_lub_ewidencyjna":
            "/YES",

        "cel_CL1_potrzeby_wlasne":
            "/YES",

        "wysylka_email":
            "/YES"
    }

    # ----------------------------
    # FORMULARZ P1
    # ----------------------------

    pola_p1 = {

        "jednostka_ewidencyjna_obreb":
            data.formularz_P1.get("obreb", ""),

        "identyfikator_dzialki_numer_dzialki":
            data.formularz_P1.get("numer_dzialki", ""),

        "liczba_egzemplarzy":
            str(data.formularz_P1.get("liczba_egzemplarzy", "")),

        # checkboxy
        "mapa_ewidencji_gruntow_i_budynkow":
            "/YES",

        "postac_rastrowa":
            "/YES",

        # UWAGA:
        # skale mają export value /No
        "skala_1_1000":
            "/No",

        "kolorystyka_kolorowa":
            "/YES"
    }

    # generowanie PDF
    wypelnij_pdf(
        "FormularzP.pdf",
        output_p,
        pola_p
    )

    wypelnij_pdf(
        "FormularzP1.pdf",
        output_p1,
        pola_p1
    )

    return {

        "status": "ok",

        "pdf_P_url":
            f"http://127.0.0.1:8002/generated/FormularzP_{uid}.pdf",

        "pdf_P1_url":
            f"http://127.0.0.1:8002/generated/FormularzP1_{uid}.pdf"
    }