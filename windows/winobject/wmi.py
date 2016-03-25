import windows
import ctypes
import struct
import functools

from ctypes.wintypes import *

import windows.com
from windows.generated_def.winstructs import *
from windows.generated_def.interfaces import IWbemLocator, IWbemServices, IEnumWbemClassObject, IWbemClassObject


class ImprovedSAFEARRAY(windows.generated_def.winstructs.SAFEARRAY):
        @classmethod
        def of_type(cls, addr, t):
            self = cls.from_address(addr)
            self.elt_type = t
            return self

        def to_list(self, t=None):
            if t is None:
                if hasattr(self, "elt_type"):
                    t = self.elt_type
                else:
                    raise ValueError("Missing type of the array")
            if self.cDims !=  1:
                raise NotImplementedError("tagSAFEARRAY if dims != 1")

            nb_element = self.rgsabound[0].cElements
            llbound = self.rgsabound[0].lLbound
            if self.cbElements != ctypes.sizeof(t):
                raise ValueError("Size of elements != sizeof(type)")
            data = [t.from_address(self.pvData + (i + llbound) * ctypes.sizeof(t)).value for i in range(nb_element)]
            return data




class WmiRequester(object):
    """Perform WMI request: NOT STABLE"""
    INSTANCE = None


    def __new__(cls):
        if cls.INSTANCE is not None:
            return cls.INSTANCE
        cls.INSTANCE = super(cls, cls).__new__(cls)
        return cls.INSTANCE

    def __init__(self):
        locator = IWbemLocator()
        service = IWbemServices()
        CLSID_WbemAdministrativeLocator_IID = windows.com.IID.from_string('CB8555CC-9128-11D1-AD9B-00C04FD8FDFF')

        windows.com.init()
        windows.com.create_instance(CLSID_WbemAdministrativeLocator_IID, locator)
        locator.ConnectServer("root\\cimv2", None, None , None, 0x80, None, None, ctypes.byref(service))
        self.service = service

    def select(self, frm, attrs="*"):
        """Select `attrs` from ``frm``

            :rtype: list of dict
        """
        enumerator = IEnumWbemClassObject()
        try:
            self.service.ExecQuery("WQL", "select * from {0}".format(frm), 0x20, 0, ctypes.byref(enumerator))
        except WindowsError as e:
            if (e.winerror & 0xffffffff) ==  WBEM_E_INVALID_CLASS:
                raise WindowsError(e.winerror, 'WBEM_E_INVALID_CLASS <Invalid WMI class "{0}">'.format(frm))
            raise

        count = ctypes.c_ulong(0)
        processor = IWbemClassObject()
        res = []
        enumerator.Next(0xffffffff, 1, ctypes.byref(processor), ctypes.byref(count))
        while count.value:
            current_res = {}
            variant_res = windows.com.ImprovedVariant()
            if attrs == "*":
                attrs = [x for x in self.get_names(processor) if not x.startswith("__")]
            for name in attrs:
                processor.Get(name, 0, ctypes.byref(variant_res), None, None)
                # TODO: something clean and generic
                if variant_res.vt & VT_ARRAY:
                    if variant_res.vt & VT_TYPEMASK == VT_BSTR:
                        current_res[name] = variant_res._Data.parray[0].to_list(BSTR)
                    if variant_res.vt & VT_TYPEMASK == VT_I4:
                        current_res[name] = variant_res._Data.parray[0].to_list(LONG)
                elif variant_res.vt in [VT_EMPTY, VT_NULL]:
                    current_res[name] = None
                elif variant_res.vt == VT_BSTR:
                    current_res[name] = variant_res.asbstr
                elif variant_res.vt == VT_I4:
                    current_res[name] = variant_res.aslong
                elif variant_res.vt == VT_BOOL:
                    current_res[name] = variant_res.asbool
                else:
                    print("Ignore variant of type {0}".format(hex(variant_res.vt)))
            res.append(current_res)
            enumerator.Next(0xffffffff, 1, ctypes.byref(processor), ctypes.byref(count))
        return res

    def get_names(self, processor):
        res = POINTER(SAFEARRAY)()
        processor.GetNames(None, 0, None, byref(res))
        safe_array = ctypes.cast(res, POINTER(ImprovedSAFEARRAY))[0]
        safe_array.elt_type = BSTR
        return safe_array.to_list()