/** @odoo-module **/

import {Component, onMounted, useRef, useState, useEnv, useEffect} from "@odoo/owl"
import {Downloader} from "../downloader/downloader";
import {SignableObject} from "../../helpers/signable";


export class EUSigner extends Component {
    static template = "eusign_cp.owl_signer_template"
    static components = {Downloader}
    static props = {
        url_xml_http_proxy_service: {type: String, required: true},
        url_get_certificates: {type: String, required: true},
        url_cas: {type: String, required: true},
    }

    onKeyDown(ev) {
        if (ev.key === 'Enter') {
            this.readPrivateKeyButtonClick();
        }   
    }

    openPrivateKeyFileDialog() {
        if (this.state.privateKeyReaded) {
            return;
        }
        this.PKeyFileInput.el.click();
    }

    onPrivateKeyPasswordInput(event) {
        this.state.pkey_password = event.target.value;
    }

    loadFilesFromLocalStorage(localStorageFolder, loadFunc) {
        if (!this.utils.IsStorageSupported())
            this.euSign.RaiseError(EU_ERROR_NOT_SUPPORTED);

        if (this.utils.IsFolderExists(localStorageFolder)) {
            const files = this.utils.GetFiles(localStorageFolder);
            for (let i = 0; i < files.length; i++) {
                const file = this.utils.ReadFile(
                    localStorageFolder, files[i]);
                loadFunc(files[i], file);
            }
            return files;
        } else {
            this.utils.CreateFolder(localStorageFolder);
            return null;
        }
    }

    onChangeFileToSign(ev) {
        this.state.file_loaded = ev.target.files.length > 0 && this.euSign.IsPrivateKeyReaded()
    }

    updateStorageList(listName, items, emptyMessage, errorMessage, hasError = false) {
        if (hasError) {
            this.state[listName] = [];
            this.state[`${listName}_message`] = errorMessage;
            return;
        }
        if (items != null && items.length > 0) {
            this.state[listName] = items;
            this.state[`${listName}_message`] = "";
            return;
        }
        this.state[listName] = [];
        this.state[`${listName}_message`] = emptyMessage;
    }

    readPrivateKeyButtonClick() {
        const certificatesFiles = this.privateKeyCerts;
        const self = this;

        const _onError = function (e) {
            // setStatus('');
            // alert(e);
            self.file_loaded = false
            self.setAlert(e, 'alert-danger')
        };

        const _onSuccess = function (keyName, key) {
            self.readPrivateKey(keyName, new Uint8Array(key),
                self.state.pkey_password, null, false);
        };

        try {
            if (!this.state.privateKeyReaded) {
                // setStatus('зчитування ключа');

                const files = this.PKeyFileInput.el.files;

                if (files.length !== 1) {
                    _onError("Виникла помилка при зчитуванні особистого ключа. " +
                        "Опис помилки: файл з особистим ключем не обрано");
                    return;
                }

                if (this.state.pkey_password === "") {
                    this.PKeyPassword.el.focus();
                    _onError("Виникла помилка при зчитуванні особистого ключа. " +
                        "Опис помилки: не вказано пароль доступу до особистого ключа");
                    return;
                }

                if (this.state.loadPKCertsFromFile &&
                    (certificatesFiles == null ||
                        certificatesFiles.length <= 0)) {
                    _onError("Виникла помилка при зчитуванні особистого ключа. " +
                        "Опис помилки: не обрано жодного сертифіката відкритого ключа");
                    return;
                }

                const _onFileRead = function (readedFile) {
                    _onSuccess(readedFile.file.name, readedFile.data);
                };

                this.euSign.ReadFile(files[0], _onFileRead, _onError);
            } else {
                this.file_loaded = false
                this.state.certificates = []
                this.onChangeMenuItem()
            }
        } catch (e) {
            _onError(e.message);
        }
    }

    onChangeMenuItem() {

        this.removeStoredPrivateKey();
        this.euSign.ResetPrivateKey();
        this.privateKeyReaded(false);
        this.state.pkey_password = "";
        this.state.pkey_file_name = "";
        this.state.can_enter_password = false;
        this.PKeyFileInput.el.value = null
        this.clearPrivateKeyCertificatesList();
        this.sharedState.status_key = "";
        this.utils.RemoveSessionStorageItem(
            this.CACertificatesSessionStorageName);
        // this.fileElem.el.value = null
    }

    clearPrivateKeyCertificatesList() {
        this.privateKeyCerts = null;
    }

    selectPrivateKeyFile(event) {
        const enable = (event.target.files.length === 1);
        this.state.can_enter_password = enable
        this.state.pkey_file_name = enable ? event.target.files[0].name : ''
        this.state.pkey_password = ''
        this.state.privateKeyReaded = this.euSign.IsPrivateKeyReaded()
        this.state.file_loaded = event.target.files.length > 0 && this.euSign.IsPrivateKeyReaded()
    }

    loadCertsAndCRLsFromLocalStorage() {
        try {
            const files = this.loadFilesFromLocalStorage(
                this.CertsLocalStorageName,
                (fileName, fileData) => {
                    if (fileName.indexOf(".cer") >= 0)
                        this.euSign.SaveCertificate(fileData);
                    else if (fileName.indexOf(".p7b") >= 0)
                        this.euSign.SaveCertificates(fileData);
                });
            this.updateStorageList(
                "selected_certs",
                files,
                "Сертифікати відсутні в локальному сховищі",
                "Виникла помилка при завантаженні сертифікатів з локального сховища"
            );
        } catch (e) {
            this.updateStorageList(
                "selected_certs",
                null,
                "Сертифікати відсутні в локальному сховищі",
                "Виникла помилка при завантаженні сертифікатів з локального сховища",
                true
            );
        }

        try {
            const files = this.loadFilesFromLocalStorage(
                this.CRLsLocalStorageName,
                (fileName, fileData) => {
                    if (fileName.indexOf(".crl") >= 0) {
                        try {
                            this.euSign.SaveCRL(true, fileData);
                        } catch (e) {
                            this.euSign.SaveCRL(false, fileData);
                        }
                    }
                });
            this.updateStorageList(
                "selected_crls",
                files,
                "СВС відсутні в локальному сховищі",
                "Виникла помилка при завантаженні СВС з локального сховища"
            );
        } catch (e) {
            this.updateStorageList(
                "selected_crls",
                null,
                "СВС відсутні в локальному сховищі",
                "Виникла помилка при завантаженні СВС з локального сховища",
                true
            );
        }

    }

    signTypeASiCSelectOnChange(el) {
        const index = parseInt(this.signTypeASiCSelect.el.value)
        if (index === 1) {
            this.state.PadesSelected = false
            this.state.XadesSelected = false
            this.state.CadesSelected = true
        } else {
            this.state.PadesSelected = false
            this.state.XadesSelected = true
            this.state.CadesSelected = false
        }
    }

    SignFormatOnChange(el) {
        const index = parseInt(this.SignFormat.el.value)
        switch (index) {
            case 1: {
                this.state.PadesSelected = false
                this.state.XadesSelected = true
                this.state.CadesSelected = false
                this.state.AsicSelected = false
                break
            }
            case 2: {
                this.state.PadesSelected = true
                this.state.XadesSelected = false
                this.state.CadesSelected = false
                this.state.AsicSelected = false
                break
            }
            case 3: {
                this.state.PadesSelected = false
                this.state.XadesSelected = false
                this.state.CadesSelected = true
                this.state.AsicSelected = false
                break
            }
            default: {
                const asic_type = parseInt(this.signTypeASiCSelect.el.value)
                this.state.PadesSelected = false
                this.state.XadesSelected = asic_type === 2
                this.state.CadesSelected = asic_type === 1
                this.state.AsicSelected = true
                break
            }
        }
    }

    signFormatPAdESSelectOnChange() {
        const index = parseInt(this.signFormatPAdESSelect.el.value)
        if (index === EU_PADES_SIGN_LEVEL_B_B) {
            this.setAlert('Звертаємо Вашу увагу на те, що із набуттям чинності 07.11.2018 Закону України «Про електронну ідентифікацію та електронні довірчі послуги» та відповідно до частини четвертої статті 26 цього закону, використання кваліфікованої електронної позначки часу для постійного зберігання електронних даних є обов’язковим.', 'alert-warning')
        }

    }

    signFormatXAdESSelectOnChange() {
        const index = parseInt(this.signFormatXAdESSelect.el.value)
        if (index === EU_XADES_SIGN_LEVEL_B_B) {
            this.setAlert('Звертаємо Вашу увагу на те, що із набуттям чинності 07.11.2018 Закону України «Про електронну ідентифікацію та електронні довірчі послуги» та відповідно до частини четвертої статті 26 цього закону, використання кваліфікованої електронної позначки часу для постійного зберігання електронних даних є обов’язковим.', 'alert-warning')
        }
    }

    signFileEx() {
        const file = this.FileToSign.el.files[0];
        const self = this;
        if (this.state.sign_completed) {
            this.state.sign_completed = false
            this.FileToSign.el.value = ''
            this.state.file_loaded = false
            this.state.signed_files = []
            return
        }

        if (!file) {
            this.setAlert('Файл для підпису не обрано. Оберіть файл', 'alert-danger')
            return;
        }

        if (file.size > Module.MAX_DATA_SIZE) {
            this.setAlert("Розмір файлу для піпису занадто великий. Оберіть файл меншого розміру", 'alert-warning')
            return;
        }
        if (!this.euSign.IsPrivateKeyReaded()) {
            this.setAlert("Особистий ключ не зчитано!", 'alert-danger')
            return;
        }
        const formatSign = parseInt(this.SignFormat.el.value)

        const fileReader = new FileReader();

        fileReader.onloadend = ((fileName) => {
            return (evt) => {
                if (evt.target.readyState !== FileReader.DONE)
                    return;
                const data = new Uint8Array(evt.target.result),
                    signed_files = [], info = {}
                if (formatSign === 1) {
                    try {
                        if (!fileName.endsWith('.xml')) {
                            throw new Error('Файл для підпису має бути у форматі XML')
                        }
                        const xadesType = parseInt(self.SignType.el.value) === 2 ? EU_XADES_TYPE_ENVELOPED : EU_XADES_TYPE_DETACHED,
                            signLevel = parseInt(self.signFormatXAdESSelect.el.value),
                            obj = new SignableObject(fileName, data),
                            files = [obj],
                            sign = self.euSign.XAdESSignData(xadesType, signLevel, files, false)

                        self.state.sign_completed = true
                        self.setAlert("Файл успішно підписано", 'alert-success')
                        info.serial = fileName
                        info.keyUsage = 'Цифровий підпис'
                        info.certificate = sign
                        signed_files.push(info)

                    } catch (e) {
                        self.setAlert(e.message, 'alert-danger')
                    }
                } else if (formatSign === 2) {
                    try {
                        if (!fileName.endsWith('.pdf')) {
                            throw new Error('Файл для підпису має бути у форматі PDF')
                        }
                        const signType = parseInt(self.signFormatPAdESSelect.el.value),
                            sign = self.euSign.PDFSignData(data, signType, false)
                        self.state.sign_completed = true
                        self.setAlert("Файл успішно підписано", 'alert-success')
                        info.serial = fileName
                        info.keyUsage = 'Цифровий підпис'
                        info.certificate = sign
                        signed_files.push(info)
                        // self.saveFile(fileName, sign)
                    } catch (e) {
                        self.setAlert(e.message, 'alert-danger')
                    }
                } else if (formatSign === 3) {
                    const isInternalSign = parseInt(self.SignType.el.value) === 2
                    const isAddCert = true;
                    const dsAlgType = parseInt(self.DSAlgTypeSelect.el.value);


                    try {
                        let sign;

                        if (dsAlgType === 1) {
                            if (isInternalSign)
                                sign = self.euSign.SignDataInternal(isAddCert, data, false);
                            else
                                sign = self.euSign.SignData(data, false);
                        } else {
                            sign = self.euSign.SignDataRSA(data, isAddCert,
                                !isInternalSign, false);
                        }
                        self.state.sign_completed = true
                        self.setAlert("Файл успішно підписано", 'alert-success')
                        // self.saveFile(fileName + ".p7s", sign);
                        info.serial = fileName + ".p7s"
                        info.keyUsage = 'Цифровий підпис'
                        info.certificate = sign
                        signed_files.push(info)

                    } catch (e) {
                        // setStatus('');
                        // alert(e);
                        self.setAlert(e.message, 'alert-danger')
                    }
                } else if (formatSign > 3) {
                    try {
                        const asicType = formatSign === 4 ? EU_ASIC_TYPE_E : EU_ASIC_TYPE_S,
                            signType = parseInt(self.signTypeASiCSelect.el.value) === 1 ? EU_ASIC_SIGN_TYPE_CADES : EU_ASIC_SIGN_TYPE_XADES,
                            signLevel = signType === EU_ASIC_SIGN_TYPE_CADES ? this.CAdESTypes[this.DSCAdESTypeSelect.el.selectedIndex] : parseInt(self.signFormatXAdESSelect.el.value),
                            // obj = new SignableObject(fileName, signType === EU_ASIC_SIGN_TYPE_XADES ? data : evt.target.result),
                            obj = new SignableObject(fileName, data),
                            files = [obj],
                            sign = self.euSign.ASiCSignData(asicType, signType, signLevel, files, false)

                        self.state.sign_completed = true
                        self.setAlert("Файл успішно підписано", 'alert-success')

                        info.serial = fileName + (asicType === EU_ASIC_TYPE_S ? ".asics" : ".asice")
                        info.keyUsage = 'Цифровий підпис'
                        info.certificate = sign
                        signed_files.push(info)

                    } catch (e) {
                        self.setAlert(e.message, 'alert-danger')
                    }
                }
                if (signed_files.length > 0) {
                    self.state.signed_files = signed_files
                }
            };
        })(file.name);

        fileReader.readAsArrayBuffer(file);
    }

    saveFile(fileName, array) {
        const blob = new Blob([array], {type: "application/octet-stream"});
        saveAs(blob, fileName);
    }

    setDefaultSettings() {
        try {
            this.euSign.SetXMLHTTPProxyService(this.props.url_xml_http_proxy_service);

            let settings = this.euSign.CreateFileStoreSettings();
            settings.SetPath("/certificates");
            settings.SetSaveLoadedCerts(true);
            this.euSign.SetFileStoreSettings(settings);

            settings = this.euSign.CreateProxySettings();
            this.euSign.SetProxySettings(settings);

            settings = this.euSign.CreateTSPSettings();
            this.euSign.SetTSPSettings(settings);

            settings = this.euSign.CreateOCSPSettings();
            this.euSign.SetOCSPSettings(settings);

            settings = this.euSign.CreateCMPSettings();
            this.euSign.SetCMPSettings(settings);

            settings = this.euSign.CreateLDAPSettings();
            this.euSign.SetLDAPSettings(settings);

            settings = this.euSign.CreateOCSPAccessInfoModeSettings();
            settings.SetEnabled(true);
            this.euSign.SetOCSPAccessInfoModeSettings(settings);

            const CAs = this.CAsServers;
            settings = this.euSign.CreateOCSPAccessInfoSettings();
            for (let i = 0; i < CAs.length; i++) {
                settings.SetAddress(CAs[i].ocspAccessPointAddress);
                settings.SetPort(CAs[i].ocspAccessPointPort);

                for (let j = 0; j < CAs[i].issuerCNs.length; j++) {
                    settings.SetIssuerCN(CAs[i].issuerCNs[j]);
                    this.euSign.SetOCSPAccessInfoSettings(settings);
                }
            }
        } catch (e) {
            this.setAlert("Виникла помилка при встановленні налашувань: " + e.message, 'alert-danger')
        }
    }

    loadCertsFromServer() {
        const pThis = this;
        const certificates = this.utils.GetSessionStorageItem(
            this.CACertificatesSessionStorageName, true, false);
        if (certificates != null) {
            try {
                this.euSign.SaveCertificates(certificates);

                return;
            } catch (e) {
                this.setAlert("Виникла помилка при імпорті " +
                    "завантажених з сервера сертифікатів " +
                    "до файлового сховища", 'alert-danger')
            }
        }

        const _onSuccess = function (certificates) {
            try {
                pThis.euSign.SaveCertificates(certificates);
                pThis.utils.SetSessionStorageItem(
                    pThis.CACertificatesSessionStorageName,
                    certificates, false);
            } catch (e) {

                pThis.setAlert("Виникла помилка при імпорті " +
                    "завантажених з сервера сертифікатів " +
                    "до файлового сховища", 'alert-danger')
            }
        };

        const _onFail = function (errorCode) {
            console.log("Виникла помилка при завантаженні сертифікатів з сервера. " +
                "(HTTP статус " + errorCode + ")");
        };

        this.utils.GetDataFromServerAsync(this.props.url_get_certificates, _onSuccess, _onFail, true);
    }

    getCAServer() {
        const index = this.CAsServersSelect.el.selectedIndex;

        if (index < this.CAsServers.length)
            return this.CAsServers[index];

        return null;
    }

    loadCAServer() {
        const index = this.utils.GetSessionStorageItem(
            this.CAServerIndexSessionStorageName, false, false);
        if (index != null) {
            this.CAsServersSelect.el.selectedIndex = parseInt(index)

            this.setCASettings(parseInt(index));
        }
    }

    storeCAServer() {
        const index = this.CAsServersSelect.el.selectedIndex;
        return this.utils.SetSessionStorageItem(
            this.CAServerIndexSessionStorageName, index.toString(), false);
    }

    removeCAServer() {
        this.utils.RemoveSessionStorageItem(
            this.CAServerIndexSessionStorageName);
    }

    getPrivateKeyCertificatesByCMP(key, password, onSuccess, onError) {
        try {
            const cmpAddress = this.getCAServer().cmpAddress + ":80",
                keyInfo = this.euSign.GetKeyInfoBinary(key, password);
            onSuccess(this.euSign.GetCertificatesByKeyInfo(keyInfo, [cmpAddress]));
        } catch (e) {
            onError(e);
        }
    }

    getPrivateKeyCertificates(key, password, fromCache, onSuccess, onError) {
        let certificates;

        if (this.state.CAServer != null &&
            this.state.CAServer.certsInKey) {
            onSuccess([]);
            return;
        }

        if (fromCache) {
            if (this.state.useCMP) {
                certificates = this.utils.GetSessionStorageItem(
                    this.PrivateKeyCertificatesChainSessionStorageName, true, false);
            } else if (this.state.loadPKCertsFromFile) {
                certificates = this.utils.GetSessionStorageItems(
                    this.PrivateKeyCertificatesSessionStorageName, true, false)
            }

            onSuccess(certificates);
        } else if (this.state.useCMP) {
            this.getPrivateKeyCertificatesByCMP(
                key, password, onSuccess, onError);
        } else if (this.state.loadPKCertsFromFile) {
            const _onSuccess = function (files) {
                const certificates = [];
                for (let i = 0; i < files.length; i++) {
                    certificates.push(files[i].data);
                }

                onSuccess(certificates);
            };

            this.euSign.ReadFiles(
                this.privateKeyCerts,
                _onSuccess, onError);
        }
    }

    removeStoredPrivateKey() {
        this.utils.RemoveSessionStorageItem(
            this.PrivateKeyNameSessionStorageName);
        this.utils.RemoveSessionStorageItem(
            this.PrivateKeySessionStorageName);
        this.utils.RemoveSessionStorageItem(
            this.PrivateKeyPasswordSessionStorageName);
        this.utils.RemoveSessionStorageItem(
            this.PrivateKeyCertificatesChainSessionStorageName);
        this.utils.RemoveSessionStorageItem(
            this.PrivateKeyCertificatesSessionStorageName);

        this.removeCAServer();
    }

    privateKeyReaded(isReaded) {
        if (!isReaded) {
            this.state.pkey_file_name = "";
            this.state.pkey_password = "";
            this.state.can_enter_password = false;
        }
        this.state.privateKeyReaded = isReaded
    }

    DSCAdESTypeChanged() {
        const signType = this.CAdESTypes[
            this.DSCAdESTypeSelect.el.selectedIndex];
        try {
            this.euSign.SetRuntimeParameter(EU_SIGN_TYPE_PARAMETER, signType);
        } catch (e) {
            this.setAlert(e.message, 'alert-danger')
        }
    }

    applyAccordionEvents() {
        const container = this.accordionContainer.el;
        if (!container) {
            return () => {};
        }
        const accordionButtons = Array.from(container.getElementsByClassName("accordion"));
        const handlers = [];

        accordionButtons.forEach((button) => {
            const onClick = () => {
                const allPanels = container.getElementsByClassName("panel");
                for (let j = 0; j < allPanels.length; j++) {
                    if (allPanels[j] !== button.nextElementSibling) {
                        allPanels[j].style.maxHeight = null;
                        allPanels[j].previousElementSibling.classList.remove("current");
                    }
                }

                button.classList.toggle("current");
                const panel = button.nextElementSibling;
                if (panel.style.maxHeight) {
                    panel.style.maxHeight = null;
                } else {
                    panel.style.maxHeight = panel.scrollHeight + "px";
                }
            };
            button.addEventListener("click", onClick);
            handlers.push({button, onClick});
        });

        return () => {
            handlers.forEach(({button, onClick}) => {
                button.removeEventListener("click", onClick);
            });
        };
    }

    storePrivateKey(keyName, key, password, certificates) {
        if (!this.utils.SetSessionStorageItem(
                this.PrivateKeyNameSessionStorageName, keyName, false) ||
            !this.utils.SetSessionStorageItem(
                this.PrivateKeySessionStorageName, key, false) ||
            !this.utils.SetSessionStorageItem(
                this.PrivateKeyPasswordSessionStorageName, password, true) ||
            !this.storeCAServer()) {
            return false;
        }

        if (Array.isArray(certificates)) {
            if (!this.utils.SetSessionStorageItems(
                this.PrivateKeyCertificatesSessionStorageName,
                certificates, false)) {
                return false;
            }
        } else {
            if (!this.utils.SetSessionStorageItem(
                this.PrivateKeyCertificatesChainSessionStorageName,
                certificates, false)) {
                return false;
            }
        }

        return true;
    }

    pKeyInfo() {
        try {
            if (this.euSign.IsPrivateKeyReaded()) {
                let i = 0
                this.state.certificates = []
                while (true) {
                    const certInfo = this.euSign.EnumOwnCertificates(i),
                        info = {}
                    if (certInfo == null)
                        break
                    const cert = this.euSign.GetCertificate(
                            certInfo.GetIssuer(), certInfo.GetSerial()),
                        keyUsage = certInfo.GetKeyUsage()

                    info.serial = 'EU-' + certInfo.GetSerial() + '.cer'
                    info.certificate = cert
                    info.keyUsage = keyUsage
                    this.state.certificates.push(info)
                    i++
                }
            }
        } catch (e) {
            this.setAlert(e.message, 'alert-danger')
        }
    }

    readPrivateKey(keyName, key, password, certificates, fromCache) {
        const self = this;
        const _onError = (e) => {
            // setStatus('');

            if (fromCache) {
                self.removeStoredPrivateKey();
                self.privateKeyReaded(false);
            } else {
                // alert(e);
                self.setAlert(e, 'alert-danger')
            }

            // if (e.GetErrorCode != null &&
            //     e.GetErrorCode() == EU_ERROR_CERT_NOT_FOUND) {
            //
            //     euSignTest.mainMenuItemClicked(
            //         document.getElementById('MainPageMenuCertsAndCRLs'),
            //         'MainPageMenuCertsAndCRLsPage');
            // }
        };

        if (certificates == null) {
            const _onGetCertificates = (certs) => {
                if (certs == null) {
                    _onError(self.euSign.MakeError(EU_ERROR_CERT_NOT_FOUND));
                    return;
                }

                self.readPrivateKey(keyName, key, password, certs, fromCache);
            };

            this.getPrivateKeyCertificates(
                key, password, fromCache, _onGetCertificates, _onError);
            return;
        }

        try {
            if (Array.isArray(certificates)) {
                for (let i = 0; i < certificates.length; i++) {
                    this.euSign.SaveCertificate(certificates[i]);
                }
            } else {
                this.euSign.SaveCertificates(certificates);
            }

            this.euSign.ReadPrivateKeyBinary(key, password);

            if (!fromCache && this.utils.IsSessionStorageSupported()) {
                if (!this.storePrivateKey(
                    keyName, key, password, certificates)) {
                    this.removeStoredPrivateKey();
                }
            }

            this.privateKeyReaded(true);
            this.file_loaded = this.FileToSign.el.files.length > 0
            this.pKeyInfo()

            if (!fromCache)
                this.showOwnerInfo();
            this.setAlert('Особистий ключ успішно завантажено!', 'alert-success')
        } catch (e) {
            _onError(e.message);
        }
    }

    showOwnerInfo() {
        try {
            const ownerInfo = this.euSign.GetPrivateKeyOwnerInfo();
            this.sharedState.status_key = "Власник: " + ownerInfo.GetSubjCN() + "\n" +
                "ЦСК: " + ownerInfo.GetIssuerCN() + "\n" +
                "Серійний номер: " + ownerInfo.GetSerial()
        } catch (e) {
            this.setAlert(e.message, 'alert-danger')
        }
    }

    readPrivateKeyAsStoredFile() {
        const self = this
        const keyName = this.utils.GetSessionStorageItem(
            this.PrivateKeyNameSessionStorageName, false, false);
        const key = this.utils.GetSessionStorageItem(
            this.PrivateKeySessionStorageName, true, false);
        const password = this.utils.GetSessionStorageItem(
            this.PrivateKeyPasswordSessionStorageName, false, true);
        if (keyName == null || key == null || password == null)
            return;

        this.loadCAServer();

        this.state.pkey_file_name = keyName
        this.state.pkey_password = password
        this.state.can_enter_password = true
        const _readPK = async () => {
            await self.readPrivateKey(keyName, key, password, null, true);
            if (self.euSign.IsPrivateKeyReaded()) {
                self.showOwnerInfo();
            }
        };
        setTimeout(_readPK, 10);

        return;
    }

    initialize() {
        const pThis = this;
        // this.state.loaded = false
        const _onSuccess = () => {
            try {
                pThis.euSign.Initialize();
                pThis.euSign.SetJavaStringCompliant(true);
                pThis.euSign.SetCharset("UTF-16LE");

                pThis.euSign.SetRuntimeParameter(
                    EU_MAKE_PKEY_PFX_CONTAINER_PARAMETER, true);

                if (pThis.euSign.DoesNeedSetSettings()) {
                    pThis.setDefaultSettings();

                    if (pThis.utils.IsStorageSupported()) {
                        pThis.loadCertsAndCRLsFromLocalStorage();
                    } else {
                        pThis.updateStorageList(
                            "selected_certs",
                            null,
                            "Локальне сховище не підтримується",
                            "Локальне сховище не підтримується",
                            true
                        );
                        pThis.updateStorageList(
                            "selected_crls",
                            null,
                            "Локальне сховище не підтримується",
                            "Локальне сховище не підтримується",
                            true
                        );
                    }
                }

                pThis.loadCertsFromServer();
                pThis.setCASettings(0);

                if (pThis.utils.IsSessionStorageSupported()) {
                    const _readPrivateKeyAsStoredFile = () => {
                        pThis.readPrivateKeyAsStoredFile();
                    };
                    setTimeout(_readPrivateKeyAsStoredFile, 10);
                }
                pThis.DSCAdESTypeChanged()

            } catch (e) {
                pThis.setAlert(e.message, 'alert-danger')
            }
        };

        const _onError = () => {
            pThis.setAlert('Виникла помилка ' +
                'при завантаженні криптографічної бібліотеки', 'alert-danger')
        };
        this.loadCAsSettings(_onSuccess, _onError);
    }

    setCASettings(caIndex) {
        try {
            const caServer = (caIndex < this.CAsServers.length) ?
                this.CAsServers[caIndex] : null;
            const offline = ((caServer === null) ||
                (caServer.address === "")) ?
                true : false;
            const useCMP = (!offline && (caServer.cmpAddress !== ""));
            const loadPKCertsFromFile = (caServer === null) ||
                (!useCMP && !caServer.certsInKey);

            this.state.CAServer = caServer;
            this.state.offline = offline;
            this.state.useCMP = useCMP;
            this.state.loadPKCertsFromFile = loadPKCertsFromFile;

            let settings;

            this.clearPrivateKeyCertificatesList();

            settings = this.euSign.CreateTSPSettings();
            if (!offline) {
                settings.SetGetStamps(true);
                if (caServer.tspAddress !== "") {
                    settings.SetAddress(caServer.tspAddress);
                    settings.SetPort(caServer.tspAddressPort);
                } else {
                    settings.SetAddress('acskidd.gov.ua');
                    settings.SetPort('80');
                }
            }
            this.euSign.SetTSPSettings(settings);

            settings = this.euSign.CreateOCSPSettings();
            if (!offline) {
                settings.SetUseOCSP(true);
                settings.SetBeforeStore(true);
                settings.SetAddress(caServer.ocspAccessPointAddress);
                settings.SetPort("80");
            }
            this.euSign.SetOCSPSettings(settings);

            settings = this.euSign.CreateCMPSettings();
            settings.SetUseCMP(useCMP);
            if (useCMP) {
                settings.SetAddress(caServer.cmpAddress);
                settings.SetPort("80");
            }
            this.euSign.SetCMPSettings(settings);

            settings = this.euSign.CreateLDAPSettings();
            this.euSign.SetLDAPSettings(settings);
        } catch (e) {
            this.setAlert("Виникла помилка при встановленні налашувань: " + e.message, 'alert-danger')
        }
    }

    onchangeCASettings(event) {
        this.setCASettings(event.target.selectedIndex);
    }

    loadCAsSettings(onSuccess, onError) {
        const pThis = this;

        const _onSuccess = function (casResponse) {
            try {
                const servers = JSON.parse(casResponse.replace(/\\'/g, "'"));

                const select = pThis.CAsServersSelect.el;
                for (let i = 0; i < servers.length; i++) {
                    const option = document.createElement("option");
                    option.text = servers[i].issuerCNs[0];
                    select.add(option);
                }

                pThis.CAsServers = servers;

                onSuccess();
            } catch (e) {
                onError();
            }
        };

        this.euSign.LoadDataFromServer(this.props.url_cas, _onSuccess, onError, false);
    }

    setAlert(message, className, closeButton = false) {
        this.utils.alert(message, className, closeButton);
        // this.notification.add(message, {
        //     title: "Unknown barcode command",
        //     type: className === 'alert-success' ? "info" : className ==='alert-warning' ? "warning" : "danger",
        //     sticky: closeButton,
        // });
    }

    setup() {
        this.env = useEnv()
        this.sharedState = this.env.sharedState.state
        // this.notification = useService("notification")

        this.state = useState({
            CadesSelected: false,
            PadesSelected: false,
            XadesSelected: false,
            AsicSelected: false,
            file_loaded: false,
            privateKeyReaded: false,
            certificates: [],
            signed_files: [],
            sign_button_disabled: false,
            sign_completed: false,
            selected_certs: [],
            selected_certs_message: "",
            selected_crls: [],
            selected_crls_message: "",
            pkey_file_name: "",
            pkey_password: "",
            can_enter_password: false,

        })

        this.CAdESTypes = [
            EU_SIGN_TYPE_CADES_BES,
            EU_SIGN_TYPE_CADES_T,
            EU_SIGN_TYPE_CADES_C,
            EU_SIGN_TYPE_CADES_X_LONG,
            EU_SIGN_TYPE_CADES_X_LONG | EU_SIGN_TYPE_CADES_X_LONG_TRUSTED
        ];
        this.euSign = EUSignCP();
        this.utils = Utils(this.euSign);

        this.CACertificatesSessionStorageName = "CACertificates"
        this.CAServerIndexSessionStorageName = "CAServerIndex"
        this.CertsLocalStorageName = "Certificates"
        this.CRLsLocalStorageName = "CRLs"
        this.PrivateKeyNameSessionStorageName = "PrivateKeyName"
        this.PrivateKeySessionStorageName = "PrivateKey"
        this.PrivateKeyPasswordSessionStorageName = "PrivateKeyPassword"
        this.PrivateKeyCertificatesSessionStorageName = "PrivateKeyCertificates"
        this.PrivateKeyCertificatesChainSessionStorageName = "PrivateKeyCertificatesChain"
        this.privateKeyCerts = null
        this.CAsServersSelect = useRef("CAsServersSelect")
        this.PKeyPassword = useRef("PKeyPassword")
        this.PKeyReadButton = useRef("PKeyReadButton")
        this.PKeyFileInput = useRef("PKeyFileInput")
        this.DSCAdESTypeSelect = useRef("DSCAdESTypeSelect")
        this.FileToSign = useRef("FileToSign")
        this.DSAlgTypeSelect = useRef("DSAlgTypeSelect")
        this.alertMessage = useRef("alertMessage")
        this.SignButton = useRef("SignButton")
        this.SignType = useRef("SignType")
        this.SignFormat = useRef("SignFormat")
        this.signFormatXAdESSelect = useRef("signFormatXAdESSelect")
        this.signFormatPAdESSelect = useRef("signFormatPAdESSelect")
        this.signTypeASiCSelect = useRef("signTypeASiCSelect")
        this.accordionContainer = useRef("accordionContainer")

        useEffect((isKeyReaded, signedFiles) => {
            this.state.sign_button_disabled = !isKeyReaded || signedFiles.length > 0
            if (!isKeyReaded && signedFiles.length > 0) {
                this.state.sign_completed = false
                this.FileToSign.el.value = ''
                this.state.file_loaded = false
                this.state.signed_files = []
            }

        }, () => [this.state.privateKeyReaded, this.state.signed_files])

        useEffect(() => {
            const handleBeforeUnload = (event) => {
                this.onChangeMenuItem()
            };
            window.addEventListener("beforeunload", handleBeforeUnload);
            return () => {
                window.removeEventListener("beforeunload", handleBeforeUnload);
            };
        }, () => [])

        useEffect(() => {
            return this.applyAccordionEvents()
        }, () => [this.accordionContainer.el])

        useEffect((container) => {
            if (!container) {
                return () => {};
            }
            const downloaders = container.querySelectorAll(".panel .downloader");

            const resizeObserver = new ResizeObserver((entries) => {
                entries.forEach((entry) => {
                    const panel = entry.target.closest(".panel")
                    if (panel && panel.style.maxHeight) {
                        panel.style.maxHeight = panel.scrollHeight + "px";
                    }
                })
            })
            downloaders.forEach((downloader) => {
                resizeObserver.observe(downloader);
            })
            return () => {
                downloaders.forEach((downloader) => {
                    resizeObserver.unobserve(downloader);
                })
            }
        }, () => [this.accordionContainer.el])

        onMounted(async () => {
            await this.initialize()
            setTimeout(() => {
                this.sharedState.loaded = true
                this.SignFormatOnChange()
            }, 1000)
        })
    }
}