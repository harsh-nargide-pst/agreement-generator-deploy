import { createContext, useContext, ReactNode, useEffect, useRef } from "react";
import useApi, { BackendEndpoints } from "./useApi";
import { useUser } from "@clerk/clerk-react";
import { Agreement, TemplateAgreement } from "../types/types";

interface AgreementContextType {
  agreements: Agreement[] | null;
  loadRentAgreemnts: boolean;
  fetchAgreements: (method: {}) => Promise<void>;
  templateAgreement: TemplateAgreement[] | null;
  loadTemplatetAgreemnts: boolean;
  fetchTemplateAgreements: (method: {}) => Promise<void>;
}

const AgreementsContext = createContext<AgreementContextType>({
  agreements: [],
  loadRentAgreemnts: false,
  fetchAgreements: async (_method: {}) => {},
  templateAgreement: [],
  loadTemplatetAgreemnts: false,
  fetchTemplateAgreements: async (_method: {}) => {},
});

export const AgreementsProvider = ({ children }: { children: ReactNode }) => {
  const { user } = useUser();
  const hasFetchedRef = useRef(false);

  const {
    data: agreements,
    loading: loadRentAgreemnts,
    fetchData: fetchAgreements,
  } = useApi<Agreement[]>(BackendEndpoints.GetAgreements);
  const {
    data: templateAgreement,
    loading: loadTemplatetAgreemnts,
    fetchData: fetchTemplateAgreements,
  } = useApi<TemplateAgreement[]>(BackendEndpoints.GetTemplateAgreements);

  useEffect(() => {
    if (user?.id && !hasFetchedRef.current) {
      fetchAgreements({ method: "GET", params: { user_id: user.id } });
      fetchTemplateAgreements({ method: "GET", params: { user_id: user.id } });
      hasFetchedRef.current = true;
    }
  }, []);

  return (
    <AgreementsContext.Provider
      value={{
        agreements,
        loadRentAgreemnts,
        fetchAgreements,
        templateAgreement,
        loadTemplatetAgreemnts,
        fetchTemplateAgreements,
      }}
    >
      {children}
    </AgreementsContext.Provider>
  );
};

export const useAgreements = () => useContext(AgreementsContext);
