import { useState, useEffect, useRef } from "react";
import {
  Stepper,
  Button,
  Group,
  TextInput,
  Box,
  NumberInput,
  Loader,
  Text,
  Card,
  Center,
  ThemeIcon,
  useMantineColorScheme,
  Title,
  Divider,
  Container,
  Radio,
  MultiSelect,
  Select,
  Stack,
} from "@mantine/core";
import { IconCheck } from "@tabler/icons-react";
import { useForm } from "@mantine/form";
import { DatePickerInput } from "@mantine/dates";
import { COLORS } from "../colors";
import useApi, { BackendEndpoints } from "../hooks/useApi";
import { useAgreements } from "../hooks/useAgreements";
import { OTPInput } from "../components/agreements/OTPInput";
import { useUser } from "@clerk/clerk-react";
import {
  OTPVerificationResponse,
  OtpState,
  TenantsOtpState,
  getSuccessOtpState,
  getFailureOtpState,
  getDefaultOtpState,
} from "../types/otp";
import { AddressForm } from "../components/AddressForm";
import { FurnitureAppliances } from "../components/FurnitureAppliances";
export function AgreementGenerator() {
  const { user } = useUser();
  const [active, setActive] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showMessage, setShowMessage] = useState(false);
  const { colorScheme } = useMantineColorScheme();
  const { fetchData } = useApi(BackendEndpoints.CreateAgreement);
  const { fetchAgreements } = useAgreements();
  const { data, fetchData: verifyOTP } = useApi<OTPVerificationResponse>(
    BackendEndpoints.VerifyOTP
  );
  const { fetchData: sendOTP } = useApi(BackendEndpoints.SentOTP);
  const [otpIndex, setOtpIndex] = useState<number | null>(null);
  const [furnitureList, setFurnitureList] = useState<
    { name: string; quantity: number }[]
  >([]);
  const [furnishingType, setFurnishingType] = useState("");
  const [ownerOtpState, setOwnerOtpState] = useState<OtpState>(
    getDefaultOtpState()
  );
  const [tenantsOtpState, setTenantsOtpState] = useState<TenantsOtpState>({});

  const [loadingStates, setLoadingStates] = useState({
    sendOwner: false,
    verifyOwner: false,
    tenants: {} as Record<number, { send: boolean; verify: boolean }>,
    witnesses: {} as Record<number, { send: boolean; verify: boolean }>,
  });
  const ownerTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startOwnerCountdown = () => {
    if (ownerOtpState.isCountdownActive) return;

    setOwnerOtpState((prev) => ({
      ...prev,
      isCountdownActive: true,
      timer: 300,
      isSent: true,
      showResendButton: false,
      error: "",
    }));
    ownerTimerRef.current = setInterval(() => {
      setOwnerOtpState((prev) => {
        if (prev.timer <= 1) {
          clearInterval(ownerTimerRef.current!);
          return {
            ...prev,
            isCountdownActive: false,
            otp: "",
            error: "OTP expired. Please request a new OTP.",
            isSent: false,
            showResendButton: true,
            timer: 0,
          };
        }
        return {
          ...prev,
          timer: prev.timer - 1,
        };
      });
    }, 1000);
  };
  const tenantTimersRef = useRef<
    Record<number, ReturnType<typeof setInterval> | null>
  >({});

  const startTenantCountdown = (index: number) => {
    if (tenantsOtpState[index]?.isCountdownActive) return;

    setTenantsOtpState((prev) => ({
      ...prev,
      [index]: {
        ...(prev[index] || getDefaultOtpState()),
        isCountdownActive: true,
        timer: 300,
        isSent: true,
        showResendButton: false,
        error: "",
      },
    }));

    tenantTimersRef.current[index] = setInterval(() => {
      setTenantsOtpState((prev) => {
        if (prev[index]?.timer <= 1) {
          clearInterval(tenantTimersRef.current[index]!);
          return {
            ...prev,
            [index]: {
              ...(prev[index] || getDefaultOtpState()),
              isCountdownActive: false,
              isSent: false,
              showResendButton: true,
              otp: "",
              error: "OTP expired. Please request a new OTP.",
              timer: 0,
            },
          };
        }
        return {
          ...prev,
          [index]: {
            ...(prev[index] || getDefaultOtpState()),
            timer: prev[index]?.timer - 1,
          },
        };
      });
    }, 1000);
  };

  const [witnessOtpState, setWitnessOtpState] = useState<Record<number, OtpState>>({});
  const witnessTimersRef = useRef<Record<number, ReturnType<typeof setInterval> | null>>({});

  const startWitnessCountdown = (index: number) => {
    if (witnessOtpState[index]?.isCountdownActive) return;

    setWitnessOtpState((prev) => ({
      ...prev,
      [index]: {
        ...(prev[index] || getDefaultOtpState()),
        isCountdownActive: true,
        timer: 300,
        isSent: true,
        showResendButton: false,
        error: "",
      },
    }));

    witnessTimersRef.current[index] = setInterval(() => {
      setWitnessOtpState((prev) => {
        if (prev[index]?.timer <= 1) {
          clearInterval(witnessTimersRef.current[index]!);
          return {
            ...prev,
            [index]: {
              ...(prev[index] || getDefaultOtpState()),
              isCountdownActive: false,
              isSent: false,
              showResendButton: true,
              otp: "",
              error: "OTP expired. Please request a new OTP.",
              timer: 0,
            },
          };
        }
        return {
          ...prev,
          [index]: {
            ...(prev[index] || getDefaultOtpState()),
            timer: prev[index]?.timer - 1,
          },
        };
      });
    }, 1000);
  };

  useEffect(() => {
    if (data) {
      const { success, type } = data;
      if (success === true) {
        if (type === "owner" && ownerOtpState.isSent) {
          setOwnerOtpState(getSuccessOtpState);
        }
        if (
          type === "tenant" &&
          otpIndex !== null &&
          tenantsOtpState[otpIndex]?.isSent
        ) {
          setTenantsOtpState((prev) => ({
            ...prev,
            [otpIndex]: getSuccessOtpState(prev[otpIndex]),
          }));
        }
        if (
          type === "witness" &&
          otpIndex !== null &&
          witnessOtpState[otpIndex]?.isSent
        ) {
          setWitnessOtpState((prev) => ({
            ...prev,
            [otpIndex]: getSuccessOtpState(prev[otpIndex]),
          }));
        }
      } else {
        if (type === "owner" && ownerOtpState.isSent) {
          setOwnerOtpState(getFailureOtpState);
        }
        if (
          type === "tenant" &&
          otpIndex !== null &&
          tenantsOtpState[otpIndex]?.isSent
        ) {
          setTenantsOtpState((prev) => ({
            ...prev,
            [otpIndex]: getFailureOtpState(prev[otpIndex]),
          }));
        }
        if (
          type === "witness" &&
          otpIndex !== null &&
          witnessOtpState[otpIndex]?.isSent
        ) {
          setWitnessOtpState((prev) => ({
            ...prev,
            [otpIndex]: getFailureOtpState(prev[otpIndex]),
          }));
        }
      }
      setOtpIndex(null);
    }
  }, [data]);

  const addFurniture = () => {
    const errors: Record<string, string> = {};
    const furnitureName = form.values.furnitureName.trim();

    if (!furnitureName) {
      errors.furnitureName = "Please enter a furniture name";
    } else if (/^\d+$/.test(furnitureName)) {
      errors.furnitureName = "Furniture name cannot be only numbers";
    }

    if (form.values.furnitureQuantity < 1) {
      errors.furnitureQuantity = "Please enter a valid furniture quantity";
    }

    if (Object.keys(errors).length > 0) {
      form.setErrors({
        furnitureName: errors.furnitureName,
        furnitureQuantity: errors.furnitureQuantity,
      });
      return;
    }
    setFurnitureList((prev) => [
      ...prev,
      {
        name: form.values.furnitureName,
        quantity: form.values.furnitureQuantity,
      },
    ]);
    form.setFieldValue("furnitureName", "");
    form.setFieldValue("furnitureQuantity", 1);
  };

  const removeFurniture = (index: number) => {
    setFurnitureList((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSendOTP = async () => {
    setLoadingStates((prev) => ({ ...prev, sendOwner: true }));
    try {
      await sendOTP({
        method: "POST",
        data: { email: form.values.ownerEmailAddress, type: "owner" },
      });
      setOwnerOtpState((prev) => ({
        ...prev,
        isSent: true,
        error: "",
        isCountdownActive: true,
      }));
      startOwnerCountdown();
    } catch (error) {
      console.error("Error sending OTP:", error);
      setOwnerOtpState((prev) => ({
        ...prev,
        error: "Failed to send OTP. Please try again.",
      }));
    } finally {
      setLoadingStates((prev) => ({ ...prev, sendOwner: false }));
    }
  };

  const handleVerifyOTP = async () => {
    setLoadingStates((prev) => ({ ...prev, verifyOwner: true }));
    try {
      await verifyOTP({
        method: "POST",
        data: {
          email: form.values.ownerEmailAddress,
          otp: ownerOtpState.otp,
          type: "owner",
        },
      });
    } catch (error) {
      console.error("Error verifying OTP:", error);
      setOwnerOtpState((prev) => ({
        ...prev,
        error: "Error verifying OTP. Please try again.",
      }));
    } finally {
      setLoadingStates((prev) => ({ ...prev, verifyOwner: false }));
    }
  };

  const handleSendTenantOTP = async (index: number) => {
    setLoadingStates((prev) => ({
      ...prev,
      tenants: {
        ...prev.tenants,
        [index]: { send: true, verify: prev.tenants[index]?.verify || false },
      },
    }));
    try {
      await sendOTP({
        method: "POST",
        data: { email: form.values.tenants[index].email, type: "tenant" },
      });
      setTenantsOtpState((prev) => ({
        ...prev,
        [index]: {
          ...(prev[index] || getDefaultOtpState()),
          isSent: true,
          error: "",
        },
      }));
      startTenantCountdown(index);
    } catch (error) {
      console.error("Error sending OTP:", error);
      setTenantsOtpState((prev) => ({
        ...prev,
        [index]: {
          ...(prev[index] || getDefaultOtpState()),
          error: "Failed to send OTP. Please try again.",
        },
      }));
    } finally {
      setLoadingStates((prev) => ({
        ...prev,
        tenants: {
          ...prev.tenants,
          [index]: {
            send: false,
            verify: prev.tenants[index]?.verify || false,
          },
        },
      }));
    }
  };

  const handleVerifyTenantOTP = async (index: number) => {
    setLoadingStates((prev) => ({
      ...prev,
      tenants: {
        ...prev.tenants,
        [index]: { send: prev.tenants[index]?.send || false, verify: true },
      },
    }));
    try {
      setOtpIndex(index);
      await verifyOTP({
        method: "POST",
        data: {
          email: form.values.tenants[index].email,
          otp: tenantsOtpState[index].otp,
          type: "tenant",
        },
      });
    } catch (error) {
      console.error("Error verifying tenant OTP:", error);
      setTenantsOtpState((prev) => ({
        ...prev,
        [index]: {
          ...(prev[index] || getDefaultOtpState()),
          error: "Invalid OTP. Please enter the correct OTP.",
        },
      }));
    } finally {
      setLoadingStates((prev) => ({
        ...prev,
        tenants: {
          ...prev.tenants,
          [index]: { send: prev.tenants[index]?.send || false, verify: false },
        },
      }));
    }
  };

  const handleSendWitnessOTP = async (index: number) => {
    setLoadingStates((prev) => ({
      ...prev,
      witnesses: {
        ...prev.witnesses,
        [index]: { send: true, verify: prev.witnesses[index]?.verify || false },
      },
    }));
    try {
      await sendOTP({
        method: "POST",
        data: { email: form.values.witnesses[index].email, type: "witness" },
      });
      setWitnessOtpState((prev) => ({
        ...prev,
        [index]: {
          ...(prev[index] || getDefaultOtpState()),
          isSent: true,
          error: "",
        },
      }));
      startWitnessCountdown(index);
    } catch (error) {
      console.error("Error sending OTP:", error);
      setWitnessOtpState((prev) => ({
        ...prev,
        [index]: {
          ...(prev[index] || getDefaultOtpState()),
          error: "Failed to send OTP. Please try again.",
        },
      }));
    } finally {
      setLoadingStates((prev) => ({
        ...prev,
        witnesses: {
          ...prev.witnesses,
          [index]: {
            send: false,
            verify: prev.witnesses[index]?.verify || false,
          },
        },
      }));
    }
  };

  const handleVerifyWitnessOTP = async (index: number) => {
    setLoadingStates((prev) => ({
      ...prev,
      witnesses: {
        ...prev.witnesses,
        [index]: { send: prev.witnesses[index]?.send || false, verify: true },
      },
    }));
    try {
      setOtpIndex(index);
      await verifyOTP({
        method: "POST",
        data: {
          email: form.values.witnesses[index].email,
          otp: witnessOtpState[index].otp,
          type: "witness",
        },
      });
    } catch (error) {
      console.error("Error verifying witness OTP:", error);
      setWitnessOtpState((prev) => ({
        ...prev,
        [index]: {
          ...(prev[index] || getDefaultOtpState()),
          error: "Invalid OTP. Please enter the correct OTP.",
        },
      }));
    } finally {
      setLoadingStates((prev) => ({
        ...prev,
        witnesses: {
          ...prev.witnesses,
          [index]: { send: prev.witnesses[index]?.send || false, verify: false },
        },
      }));
    }
  };


  const form = useForm({
    mode: "controlled",
    initialValues: {
      // Owner Details
      ownerAddress: "",
      ownerFullName: "",
      ownerAddressConfirmed: false,
      ownerEmailAddress: "",
      ownerAddressDetails: {
        flatFloor: "",
        buildingName: "",
        area: "",
        city: "",
        pincode: "",
      },

      // Tenant Details
      tenants: Array.from({ length: 2 }, () => ({
        fullName: "",
        email: "",
        address: "",
        AddressConfirmed: false,
        addressDetails: {
          flatFloor: "",
          buildingName: "",
          area: "",
          city: "",
          pincode: "",
        },
      })),
      tenantNumber: 2,
      witnesses: Array.from({ length: 2 }, () => ({
        fullName: "",
        email: "",
        address: "",
        AddressConfirmed: false,
        addressDetails: {
          flatFloor: "",
          buildingName: "",
          area: "",
          city: "",
          pincode: "",
        },
      })),
      // Agreement Details
      address: "",
      city: "",
      registrationDate: new Date(),
      rentAmount: 0,
      securityAmount: 0,
      agreementPeriod: [
        new Date(),
        new Date(new Date().setMonth(new Date().getMonth() + 6)),
      ],
      // Property Details
      amenities: [],
      propertyArea: "",
      bhkType: "",
      furnitureName: "",
      furnitureQuantity: 1,
    },

    validate: (values) => {
      const errors: Record<string, string> = {};
      const fullNameRegex = /^[A-Za-z]+(?:[\s-][A-Za-z]+)+$/;
      const emailRegex =
        /^(?!\.)[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+(\.[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+)*@[a-zA-Z0-9-]+(\.[a-zA-Z]{2,63})+$/;

      const validateAddressFields = (addressDetails: any, prefix: string) => {
        Object.entries(addressDetails).forEach(([field, value]) => {
          const error = validateField(field, value as string);
          if (error) errors[`${prefix}.${field}`] = error;
        });
      };
      if (active === 0) {
        if (!fullNameRegex.test(values.ownerFullName.trim())) {
          errors.ownerFullName =
            "Full name must include at least a first name and a surname";
        }
        if (!emailRegex.test(values.ownerEmailAddress)) {
          errors.ownerEmailAddress = "Please enter a valid email address";
        }
        validateAddressFields(
          values.ownerAddressDetails,
          "ownerAddressDetails"
        );
      }
      if (active === 1) {
        if (values.tenantNumber < 1) {
          errors.tenantNumber = "Number of tenants must be at least 1";
        }
      }
      if (active === 2) {
        values.tenants.forEach((tenant, index) => {
          if (!fullNameRegex.test(tenant.fullName.trim())) {
            errors[`tenants.${index}.fullName`] =
              "Tenant full name must include at least a first name and a surname";
          }
          if (!emailRegex.test(tenant.email)) {
            errors[`tenants.${index}.email`] =
              "Please enter a valid email address";
          }
          validateAddressFields(
            tenant.addressDetails,
            `tenants.${index}.addressDetails`
          );
        });
      }
      if (active === 3) {
        values.witnesses.forEach((witness, index) => {
          if (!fullNameRegex.test(witness.fullName.trim())) {
            errors[`witnesses.${index}.fullName`] =
              "Witness full name must include at least a first name and a surname";
          }
          if (!emailRegex.test(witness.email)) {
            errors[`witnesses.${index}.email`] =
              "Please enter a valid email address";
          }
          validateAddressFields(
            witness.addressDetails,
            `witnesses.${index}.addressDetails`
          );
        });
      }
      if (active === 5) {
        if (values.address.trim().length < 10) {
          errors.address = "Address must be at least 10 characters";
        }
        if (!values.city.trim()) {
          errors.city = "City is required";
        } else if (!/^[a-zA-Z\s]+$/.test(values.city.trim())) {
          errors.city = "City should contain characters only";
        }
        if (values.rentAmount <= 0) {
          errors.rentAmount = "Rent amount must be greater than 0";
        }
        if (values.securityAmount <= 0) {
          errors.securityAmount = "Security amount must be greater than 0";
        }
        if (values.agreementPeriod.length !== 2) {
          errors.agreementPeriod =
            "Agreement period must be a valid date range";
        } else {
          const [start, end] = values.agreementPeriod;
          const sixMonthLater = new Date(start);
          sixMonthLater.setMonth(sixMonthLater.getMonth() + 6);
          if (end < sixMonthLater) {
            errors.agreementPeriod =
              "Agreement period must be at least six months";
          }
        }
      }
      if (active === 4) {
        if (
          (furnishingType === "furnished" ||
            furnishingType === "semi-furnished") &&
          furnitureList.length === 0
        ) {
          errors.furnitureName = "Please add at least one furniture item";
        }
        if (!values.propertyArea || Number(values.propertyArea) <= 0) {
          errors.propertyArea = "Please enter a valid area in square feet";
        }
        if (!values.bhkType) {
          errors.bhkType = "Please select a BHK type";
        }
      }
      return errors;
    },
  });

  const updateTenants = (value: number) => {
    form.setFieldValue(
      "tenants",
      Array.from(
        { length: value },
        (_, index) =>
          form.values.tenants[index] || {
            fullName: "",
            email: "",
            Address: "",
            AddressConfirmed: false,
            addressDetails: {
              flatFloor: "",
              buildingName: "",
              area: "",
              city: "",
              pincode: "",
            },
          }
      )
    );
    form.setFieldValue("tenantNumber", value);
  };

  const validateField = (field: string, value: string): string => {
    let error = "";
    switch (field) {
      case "flatFloor":
        if (!/^[\w\s/,.-]+$/.test(value)) {
          error = "Flat No. & Floor should contain valid characters only";
        }
        break;
      case "buildingName":
        if (!/^[a-zA-Z0-9\s]+$/.test(value)) {
          error = "Building Name should contain characters and numbers only";
        }
        break;
      case "area":
        if (!/^[a-zA-Z0-9\s]+$/.test(value)) {
          error = "Area should contain characters and numbers only";
        }
        break;
      case "city":
        if (!/^[a-zA-Z\s]+$/.test(value)) {
          error = "City should contain characters only";
        }
        break;
      case "pincode":
        if (!/^\d+$/.test(value)) {
          error = "Pincode should contain digits only";
        } else if (value.length !== 6) {
          error = "Pincode should contain exactly 6 digits";
        }
        break;
      default:
        break;
    }
    return error;
  };

  const nextStep = () => {
    const { hasErrors } = form.validate();

    if (hasErrors) return;

    // Restrict progress on Step 1 if owner OTP is not verified
    if (active === 0) {
      if (!ownerOtpState.isVerified) {
        setOwnerOtpState((prev) => ({
          ...prev,
          error: "Please verify your OTP before proceeding.",
        }));
        return;
      }
      handleConfirmOwnerAddress();
    }

    // Restrict progress on Step 3 if any tenant OTP is not verified
    if (active === 2) {
      const unverifiedTenant = Object.values(tenantsOtpState).some(
        (state) => !state?.isVerified
      );
      if (unverifiedTenant) {
        alert("All tenants must verify their OTP before proceeding.");
        return;
      }
      form.values.tenants.forEach((_, index) =>
        handleConfirmTenantAddress(index)
      );
    }

    if (active === 3) {
      const unverifiedWitness = Object.values(witnessOtpState).some(
        (state) => !state?.isVerified
      );
      if (unverifiedWitness) {
        alert("All witnesses must verify their OTP before proceeding.");
        return;
      }
      form.values.witnesses.forEach((_, index) =>
        handleConfirmWitnessAddress(index)
      );
    }

    setActive((current) => (current < 6 ? current + 1 : current));
  };

  const prevStep = () =>
    setActive((current) => (current > 0 ? current - 1 : current));

  const handleSubmit = async () => {
    const { hasErrors } = form.validate();
    if (hasErrors) return;
    setActive((current) => (current < 6 ? current + 1 : current));
    setIsSubmitting(true);
    setShowMessage(false);
    setTimeout(() => {
      setIsSubmitting(false);
      setShowMessage(true);
      fetchAgreements({ method: "GET", params: { user_id: user?.id } });
    }, 2000);

    const transformedFurnitureList = furnitureList.map((item, index) => ({
      sr_no: (index + 1).toString(),
      name: item.name,
      units: item.quantity.toString(),
    }));

    const requestData = {
      owner_name: form.values.ownerFullName,
      owner_email: form.values.ownerEmailAddress,
      tenant_details: form.values.tenants.map((tenant) => ({
        name: tenant.fullName,
        email: tenant.email,
        address: tenant.address,
      })),
      witness_details: form.values.witnesses.map((witness) => ({
        name: witness.fullName,
        email: witness.email,
        address: witness.address,
      })),
      property_address: form.values.address,
      city: form.values.city,
      rent_amount: form.values.rentAmount,
      agreement_period: form.values.agreementPeriod.map((date) =>
        date.toISOString()
      ),
      owner_address: form.values.ownerAddress,
      furnishing_type: furnishingType,
      security_deposit: form.values.securityAmount,
      bhk_type: form.values.bhkType,
      area: form.values.propertyArea,
      registration_date: form.values.registrationDate.toISOString(),
      furniture_and_appliances: transformedFurnitureList,
      amenities: form.values.amenities,
      user_id: user?.id,
    };
    try {
      await fetchData({
        method: "POST",
        data: requestData,
      });
      await fetchAgreements({ method: "GET", params: { user_id: user?.id } });
    } catch (error) {
      console.error("Error creating agreement:", error);
    }
  };

  const handleConfirmOwnerAddress = () => {
    const fullAddress = `${form.values.ownerAddressDetails.flatFloor}, ${form.values.ownerAddressDetails.buildingName}, ${form.values.ownerAddressDetails.area}, ${form.values.ownerAddressDetails.city} - ${form.values.ownerAddressDetails.pincode}`;
    form.setFieldValue("ownerAddress", fullAddress);
  };

  const handleConfirmTenantAddress = (index: number) => {
    const tenantDetails = form.values.tenants[index].addressDetails;
    const fullAddress = `${tenantDetails.flatFloor}, ${tenantDetails.buildingName}, ${tenantDetails.area}, ${tenantDetails.city} - ${tenantDetails.pincode}`;
    form.setFieldValue(`tenants.${index}.address`, fullAddress);
  };

  const handleConfirmWitnessAddress = (index: number) => {
    const witnessDetails = form.values.witnesses[index].addressDetails;
    const fullAddress = `${witnessDetails.flatFloor}, ${witnessDetails.buildingName}, ${witnessDetails.area}, ${witnessDetails.city} - ${witnessDetails.pincode}`;
    form.setFieldValue(`witnesses.${index}.address`, fullAddress);
  };

  return (
    <>
      <Title order={3}>Generate Rent Agreement</Title>
      <Divider my="2rem" />
      <Container>
        <Stepper active={active} pt="2rem" size="xs">
          <Stepper.Step label="Step 1" description="Owner Details">
            <TextInput
              label="Full name"
              placeholder="Type owner's full name here"
              key={form.key("ownerFullName")}
              style={{ textAlign: "start" }}
              {...form.getInputProps("ownerFullName")}
              withAsterisk
            />
            <TextInput
              mt="md"
              label="Email"
              placeholder="Type owner's email address here"
              key={form.key("ownerEmailAddress")}
              style={{ textAlign: "start" }}
              {...form.getInputProps("ownerEmailAddress")}
              withAsterisk
              onChange={(event) => {
                form.setFieldValue(
                  "ownerEmailAddress",
                  event.currentTarget.value
                );
                setOwnerOtpState(getDefaultOtpState());
              }}
              disabled={
                (ownerOtpState.isSent && ownerOtpState.isCountdownActive) ||
                ownerOtpState.isVerified
              }
              rightSection={
                ownerOtpState.isVerified ? (
                  <ThemeIcon color="green" radius="xl" size="sm">
                    <IconCheck size={16} />
                  </ThemeIcon>
                ) : null
              }
            />
            <OTPInput
              otpState={ownerOtpState}
              onOtpChange={(otp) =>
                setOwnerOtpState((prev) => ({
                  ...prev,
                  otp,
                  error: otp ? "" : prev.error,
                }))
              }
              onSendOtp={handleSendOTP}
              onVerifyOtp={handleVerifyOTP}
              label="Enter Owner OTP"
              disabledSendOtp={
                !form.values.ownerEmailAddress ||
                !/^\S+@\S+\.\S+$/.test(form.values.ownerEmailAddress) ||
                (ownerOtpState.isSent && ownerOtpState.isCountdownActive) ||
                ownerOtpState.isVerified
              }
              loading={loadingStates.sendOwner || loadingStates.verifyOwner}
            />
            <Box>
              <Text size="sm" fw={500} style={{ marginBottom: 4 }}>
                Address <span style={{ color: "red" }}>*</span>
              </Text>

              <AddressForm
                addressDetails={form.values.ownerAddressDetails}
                onChange={(field, value) => {
                  form.setFieldValue(`ownerAddressDetails.${field}`, value);
                }}
                formPrefix="ownerAddressDetails"
                errors={Object.fromEntries(
                  Object.entries(form.errors)
                    .filter(([key]) => key.startsWith("ownerAddressDetails"))
                    .map(([key, value]) => [key, String(value)])
                )}
              />
            </Box>
          </Stepper.Step>

          <Stepper.Step label="Step 2" description="No. of Tenants">
            <NumberInput
              label="Number of Tenants"
              placeholder="Enter number of tenants"
              min={1}
              key={form.key("tenantNumber")}
              style={{ textAlign: "start" }}
              {...form.getInputProps("tenantNumber")}
              onChange={(value) => updateTenants(Number(value) || 1)}
              withAsterisk
            />
          </Stepper.Step>

          <Stepper.Step label="Step 3" description="Tenant Details">
            {form.values.tenants.map((_, index) => (
              <Box key={index} mt="md">
                <Title order={4} ml={0}>{`Tenant ${index + 1}`}</Title>
                <TextInput
                  label={`Full Name`}
                  placeholder="Type tenant's full name here"
                  key={form.key(`tenants.${index}.fullName`)}
                  style={{ textAlign: "start" }}
                  {...form.getInputProps(`tenants.${index}.fullName`)}
                  withAsterisk
                />
                <TextInput
                  mt="md"
                  label={`Email`}
                  placeholder="Type tenant's email address here"
                  key={form.key(`tenants.${index}.email`)}
                  style={{ textAlign: "start" }}
                  {...form.getInputProps(`tenants.${index}.email`)}
                  onChange={(event) => {
                    form.setFieldValue(
                      `tenants.${index}.email`,
                      event.currentTarget.value
                    );
                    setTenantsOtpState((prev) => ({
                      ...prev,
                      [index]: getDefaultOtpState(),
                    }));
                  }}
                  withAsterisk
                  disabled={
                    (tenantsOtpState[index]?.isSent &&
                      tenantsOtpState[index]?.isCountdownActive) ||
                    tenantsOtpState[index]?.isVerified
                  }
                  rightSection={
                    tenantsOtpState[index]?.isVerified ? (
                      <ThemeIcon color="green" radius="xl" size="sm">
                        <IconCheck size={16} />
                      </ThemeIcon>
                    ) : null
                  }
                />
                <OTPInput
                  otpState={tenantsOtpState[index] || getDefaultOtpState()}
                  onOtpChange={(value) =>
                    setTenantsOtpState((prev) => ({
                      ...prev,
                      [index]: {
                        ...(prev[index] || getDefaultOtpState()),
                        otp: value,
                        error: value ? "" : prev[index]?.error,
                      },
                    }))
                  }
                  onSendOtp={() => handleSendTenantOTP(index)}
                  onVerifyOtp={() => handleVerifyTenantOTP(index)}
                  label={`Enter OTP for Tenant ${index + 1}`}
                  disabledSendOtp={
                    !form.values.tenants[index].email ||
                    !/^\S+@\S+\.\S+$/.test(form.values.tenants[index].email) ||
                    (tenantsOtpState[index]?.isSent &&
                      tenantsOtpState[index]?.isCountdownActive) ||
                    tenantsOtpState[index]?.isVerified
                  }
                  loading={
                    loadingStates.tenants[index]?.send ||
                    loadingStates.tenants[index]?.verify
                  }
                />
                <Box>
                  <Text size="sm" fw={500} style={{ marginBottom: 4 }}>
                    Address <span style={{ color: "red" }}>*</span>
                  </Text>

                  <AddressForm
                    addressDetails={form.values.tenants[index].addressDetails}
                    onChange={(field, value) => {
                      form.setFieldValue(
                        `tenants.${index}.addressDetails.${field}`,
                        value
                      );
                    }}
                    formPrefix={`tenants.${index}.addressDetails`}
                    errors={Object.fromEntries(
                      Object.entries(form.errors)
                        .filter(([key]) =>
                          key.startsWith(`tenants.${index}.addressDetails`)
                        )
                        .map(([key, value]) => [key, String(value)])
                    )}
                  />
                </Box>
              </Box>
            ))}
          </Stepper.Step>

          <Stepper.Step label="Step 4" description="Witness Details">
            {form.values.witnesses.map((_, index) => (
              <Box key={index} mt="md">
                <Title order={4} ml={0}>{`Witness ${index + 1}`}</Title>
                <TextInput
                  label={`Full Name`}
                  placeholder="Type witness's full name here"
                  key={form.key(`witnesses.${index}.fullName`)}
                  style={{ textAlign: "start" }}
                  {...form.getInputProps(`witnesses.${index}.fullName`)}
                  withAsterisk
                />
                <TextInput
                  mt="md"
                  label={`Email`}
                  placeholder="Type witness's email address here"
                  key={form.key(`witnesses.${index}.email`)}
                  style={{ textAlign: "start" }}
                  {...form.getInputProps(`witnesses.${index}.email`)}
                  onChange={(event) => {
                    form.setFieldValue(
                      `witnesses.${index}.email`,
                      event.currentTarget.value
                    );
                    setWitnessOtpState((prev) => ({
                      ...prev,
                      [index]: getDefaultOtpState(),
                    }));
                  }}
                  withAsterisk
                  disabled={
                    (witnessOtpState[index]?.isSent &&
                      witnessOtpState[index]?.isCountdownActive) ||
                    witnessOtpState[index]?.isVerified
                  }
                  rightSection={
                    witnessOtpState[index]?.isVerified ? (
                      <ThemeIcon color="green" radius="xl" size="sm">
                        <IconCheck size={16} />
                      </ThemeIcon>
                    ) : null
                  }
                />
                <OTPInput
                  otpState={witnessOtpState[index] || getDefaultOtpState()}
                  onOtpChange={(value) =>
                    setWitnessOtpState((prev) => ({
                      ...prev,
                      [index]: {
                        ...(prev[index] || getDefaultOtpState()),
                        otp: value,
                        error: value ? "" : prev[index]?.error,
                      },
                    }))
                  }
                  onSendOtp={() => handleSendWitnessOTP(index)}
                  onVerifyOtp={() => handleVerifyWitnessOTP(index)}
                  label={`Enter OTP for Witness ${index + 1}`}
                  disabledSendOtp={
                    !form.values.witnesses[index].email ||
                    !/^\S+@\S+\.\S+$/.test(form.values.witnesses[index].email) ||
                    (witnessOtpState[index]?.isSent &&
                      witnessOtpState[index]?.isCountdownActive) ||
                    witnessOtpState[index]?.isVerified
                  }
                  loading={
                    loadingStates.witnesses[index]?.send ||
                    loadingStates.witnesses[index]?.verify
                  }
                />
                <Box>
                  <Text size="sm" fw={500} style={{ marginBottom: 4 }}>
                    Address <span style={{ color: "red" }}>*</span>
                  </Text>

                  <AddressForm
                    addressDetails={form.values.witnesses[index].addressDetails}
                    onChange={(field, value) => {
                      form.setFieldValue(
                        `witnesses.${index}.addressDetails.${field}`,
                        value
                      );
                    }}
                    formPrefix={`witnesses.${index}.addressDetails`}
                    errors={Object.fromEntries(
                      Object.entries(form.errors)
                        .filter(([key]) =>
                          key.startsWith(`witnesses.${index}.addressDetails`)
                        )
                        .map(([key, value]) => [key, String(value)])
                    )}
                  />
                </Box>
              </Box>
            ))}
          </Stepper.Step>

          <Stepper.Step label="Step 5" description="Lease property Details">
            <Stack gap="md">
              <NumberInput
                label="Area (sq. ft.)"
                placeholder="Enter area in square feet"
                key={form.key("propertyArea")}
                style={{ textAlign: "start" }}
                {...form.getInputProps("propertyArea")}
                withAsterisk
              />

              <MultiSelect
                label="Amenities (Optional)"
                placeholder="Select amenities available"
                key={form.key("amenities")}
                style={{ textAlign: "start" }}
                data={["Electricity", "Water", "Gas", "Internet", "Parking"]}
                {...form.getInputProps("amenities")}
                clearable
                searchable
              />

              <Select
                label="BHK Type"
                placeholder="Select BHK type"
                key={form.key("bhkType")}
                style={{ textAlign: "start" }}
                data={[
                  { value: "1BHK", label: "1 BHK" },
                  { value: "2BHK", label: "2 BHK" },
                  { value: "3BHK", label: "3 BHK" },
                  { value: "4BHK", label: "4 BHK" },
                ]}
                {...form.getInputProps("bhkType")}
                withAsterisk
              />

              <Radio.Group
                label="Furnishing Type"
                value={furnishingType}
                onChange={setFurnishingType}
                withAsterisk
                style={{ marginBottom: 10 }}
              >
                <Group mt="xs">
                  <Radio value="furnished" label="Furnished" />
                  <Radio value="semi-furnished" label="Semi-Furnished" />
                  <Radio value="not-furnished" label="Not Furnished" />
                </Group>
              </Radio.Group>
              {(furnishingType === "furnished" ||
                furnishingType === "semi-furnished") && (
                <FurnitureAppliances
                  furnitureList={furnitureList}
                  form={form}
                  addFurniture={addFurniture}
                  removeFurniture={removeFurniture}
                />
              )}
            </Stack>
          </Stepper.Step>
          <Stepper.Step label="Step 6" description="Agreement Details">
            <TextInput
              label="Address"
              placeholder="Address"
              key={form.key("address")}
              style={{ textAlign: "start" }}
              {...form.getInputProps("address")}
              withAsterisk
            />
            <TextInput
              label="City"
              placeholder="City"
              key={form.key("city")}
              style={{ textAlign: "start" }}
              {...form.getInputProps("city")}
              withAsterisk
            />
            <DatePickerInput
              label="Registration date"
              placeholder="Select registration date"
              minDate={new Date()}
              key={form.key("registrationDate")}
              style={{ textAlign: "start" }}
              {...form.getInputProps("registrationDate")}
              withAsterisk
            />
            <NumberInput
              label="Rent Amount"
              placeholder="Enter rent amount"
              min={0}
              key={form.key("rentAmount")}
              style={{ textAlign: "start" }}
              {...form.getInputProps("rentAmount")}
              withAsterisk
            />
            <NumberInput
              label="Security Desposit "
              placeholder="Enter Security desposit amount"
              min={0}
              key={form.key("securityAmount")}
              style={{ textAlign: "start" }}
              {...form.getInputProps("securityAmount")}
              withAsterisk
            />
            <DatePickerInput
              label="Agreement Period"
              placeholder="Select agreement period"
              minDate={new Date()}
              key={form.key("agreementPeriod")}
              style={{ textAlign: "start" }}
              {...form.getInputProps("agreementPeriod")}
              withAsterisk
              type="range"
            />
          </Stepper.Step>

          <Stepper.Completed>
            {isSubmitting ? (
              <Center>
                <Loader mt={40} />
              </Center>
            ) : (
              showMessage && (
                <Card
                  shadow="sm"
                  mt={40}
                  padding="lg"
                  withBorder
                  style={{
                    textAlign: "center",
                  }}
                >
                  <Text>
                    <ThemeIcon radius="xl" size="xl" color={COLORS.green}>
                      <IconCheck size="1.5rem" />
                    </ThemeIcon>
                  </Text>

                  <Text size="lg" fw={700} c={COLORS.green} mt="md">
                    Your agreement generation has started successfully!
                  </Text>

                  <Text size="sm" mt="sm">
                    📨 You will receive an email within a minute with a link to
                    approve the agreement.
                  </Text>

                  <Text size="lg" fw={700} c={COLORS.blue} mt="md">
                    The email link will be valid for <strong>5 minutes</strong>.
                    Please approve it within this time.
                  </Text>

                  <Text size="lg" fw={600} c={COLORS.blue} mt="md">
                    ✅ Next Steps:
                  </Text>

                  <Text
                    size="md"
                    c={
                      colorScheme === "dark"
                        ? COLORS.grayDark
                        : COLORS.grayLight
                    }
                  >
                    Open the email from us 📧 <br />
                    Click the approval link 🔗 <br />
                    Confirm the agreement to move forward ✅ <br />
                    Receive the digitally signed document 📄
                  </Text>
                  <Group justify="flex-end" mt="xl">
                    <Button
                      onClick={() => {
                        form.reset();
                        setActive(0);
                        setShowMessage(false);
                        setIsSubmitting(false);

                        if (ownerTimerRef.current)
                          clearInterval(ownerTimerRef.current);
                        Object.values(tenantTimersRef.current).forEach(
                          (timer) => (timer ? clearInterval(timer) : null)
                        );

                        setOwnerOtpState(getDefaultOtpState());
                        setTenantsOtpState({});
                        setFurnitureList([]);
                        setFurnishingType("");
                        setWitnessOtpState({});
                      }}
                    >
                      Finish
                    </Button>
                  </Group>
                </Card>
              )
            )}
          </Stepper.Completed>
        </Stepper>

        <Group justify="flex-end" mt="xl">
          {active > 0 && active < 6 && !isSubmitting && (
            <Button variant="default" onClick={prevStep}>
              Back
            </Button>
          )}
          {active < 6 && (
            <Button
              onClick={active < 5 ? nextStep : handleSubmit}
              disabled={
                (active === 0 && !ownerOtpState.isVerified) ||
                (active === 2 &&
                  Object.values(tenantsOtpState).length !==
                    form.values.tenants.length) ||
                (active === 2 &&
                  Object.values(tenantsOtpState).some(
                    (state) => !state?.isVerified
                  )) ||
                (active === 3 &&
                  Object.values(witnessOtpState).some(
                    (state) => !state?.isVerified
                  )) ||
                (active === 4 &&
                  (furnishingType === "furnished" ||
                    furnishingType === "semi-furnished") &&
                  furnitureList.length === 0)
              }
            >
              {active < 6 ? "Continue" : "Generate Agreement"}
            </Button>
          )}
        </Group>
      </Container>
    </>
  );
}
