import Config
from GACPD_Output_Processing.GACPD_Result_Processing import save_GACPD_result_data
from Making_AST.GACPD_Hunk_Info_Processing import get_GACPD_hunk_info
from Making_AST.Extract_Hunk_AST import make_hunks_AST_tree





def main ():
    save_GACPD_result_data()
    GACPD_hunks_info = get_GACPD_hunk_info()
    make_hunks_AST_tree(GACPD_hunks_info)


    print(GACPD_hunks_info)





if __name__ == "__main__":
    main()