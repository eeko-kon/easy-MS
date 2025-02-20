import streamlit as st
import plotly.express as px
from pyopenms import *
from pymetabo.helpers import Helper
from pymetabo.core import FeatureFinderMetaboIdent
from pymetabo.dataframes import DataFrames
from pymetabo.plotting import Plot
import os
import pandas as pd
from utils.filehandler import get_files, get_dir, save_file

def app():
    results_dir = "results_targeted"
    if "viewing_targeted" not in st.session_state:
        st.session_state.viewing_targeted = False
    if "mzML_files_targeted" not in st.session_state:
        st.session_state.mzML_files_targeted = set()
    if "library_options" not in st.session_state:
        st.session_state.library_options = [os.path.join("example_data", "FeatureFinderMetaboIdent", file) 
                                            for file in os.listdir(os.path.join("example_data", "FeatureFinderMetaboIdent"))]

    with st.sidebar:
        with st.expander("info", expanded=True):
            st.markdown("""
Here you can do targeted metabolomics with the FeatureFinderMetaboIdent.

As input you can add `mzML` files and select which ones to use for the chromatogram extraction.
Download the results of the summary or all selected samples and chromatograms as `tsv` or `xlsx` files.

For targeted metabolomics we have to create a table in tsv file format as specified in the [documentation](https://abibuilder.informatik.uni-tuebingen.de/archive/openms/Documentation/experimental/feature/proteomic_lfq/html/a15547.html).
In the case of this tool, the `CompoundName` can countain a `#` symbol to specifiy different adduct types of one metabolite, e.g. `GlcNAc` and `GlcNAc#+Na-H`. The intensities will be
added up in the summary. Please always enter the neutral `SumFormula` and specify the `Charge` separately. The `RetentionTime` can contain multiple values split by a comma, to
consider metabolites with double peaks as well.

Important settings that should be adopted to your data are the `extract:mz_window` and `detect:peak_width` parameters.
The `extract:n_isotopes` parameters specifies how many isotope mass traces should be included.

The results will be displayed as a summary with all samples and intensity values as well as the chromatograms and detailed information per sample. Choose the samples and chromatograms to display.
""")

    with st.expander("settings", expanded=True):
        col1, col2 = st.columns([9,1])
        with col1:
            if st.session_state.mzML_files_targeted:
                mzML_files = col1.multiselect("mzML files", st.session_state.mzML_files_targeted, st.session_state.mzML_files_targeted,
                                            format_func=lambda x: os.path.basename(x)[:-5])
            else:
                mzML_files = col1.multiselect("mzML files", [], [])
        with col2:
            st.markdown("##")
            mzML_button = st.button("Add", help="Add new mzML files.")

        col1, col2 = st.columns([9,1])
        with col1:
            library = st.selectbox("select library", st.session_state.library_options)
        with col2:
            st.markdown("##")
            load_library = st.button("Add", help="Load a library file.")

        st._arrow_table(pd.read_csv(library, sep="\t"))

        if mzML_button:
            files = get_files("Open mzML files", [("MS Data", ".mzML")])
            for file in files:
                st.session_state.mzML_files_targeted.add(file)
            st.experimental_rerun()

        if load_library:
            new_lib_files = get_files("Open library file(s)", [("Standards library", ".tsv")])
            for file in new_lib_files:
                st.session_state.library_options.insert(0, file)
            st.experimental_rerun()

        col1, col2, col3, col4 = st.columns([2,2,2,2])
        with col1:
            ffmid_mz = float(st.number_input("extract:mz_window", 0, 1000, 10))
        with col2:
            ffmid_peak_width = float(st.number_input("detect:peak_width", 1, 1000, 60))
        with col3:
            ffmid_n_isotopes = st.number_input("extract:n_isotopes", 2, 10, 2)
        with col4: 
            time_unit = st.radio("time unit", ["seconds", "minutes"])
            run_button = st.button("Extract Chromatograms!")

    if run_button:
        Helper().reset_directory(results_dir)
        for file in mzML_files:
            with st.spinner("Extracting from: " + file):

                FeatureFinderMetaboIdent().run(file,
                            os.path.join(results_dir,  os.path.basename(file[:-4]+"featureXML")), library,
                            params={"extract:mz_window": ffmid_mz,
                                    "detect:peak_width": ffmid_peak_width,
                                    "extract:n_isotopes": ffmid_n_isotopes})

                DataFrames().FFMID_chroms_to_df(os.path.join(results_dir, os.path.basename(file[:-4]+"featureXML")),
                                                os.path.join(results_dir,  os.path.basename(file[:-4]+"ftr")),
                                                time_unit=time_unit)

                DataFrames().FFMID_auc_to_df(os.path.join(results_dir,os.path.basename(file[:-4]+"featureXML")),
                                            os.path.join(results_dir,  os.path.basename(file[:-5]+"AUC.ftr")))

                DataFrames().FFMID_auc_combined_to_df(os.path.join(results_dir,  os.path.basename(file[:-5]+"AUC.ftr")),
                                                os.path.join(results_dir,  os.path.basename(file[:-5]+"AUC_combined.ftr")))

                os.remove(os.path.join(results_dir,  os.path.basename(file[:-4]+"featureXML")))


        st.session_state.viewing_targeted = True

    files = [f for f in os.listdir(results_dir) if f.endswith(".ftr") and "AUC" not in f and "summary" not in f]
    if st.session_state.viewing_targeted:
        all_files = sorted(st.multiselect("samples", files, files, format_func=lambda x: os.path.basename(x)[:-4]), reverse=True)

        DataFrames().get_auc_summary([os.path.join(results_dir, file[:-4]+"AUC.ftr") for file in all_files], os.path.join(results_dir, "summary.ftr"))
        DataFrames().get_auc_summary([os.path.join(results_dir, file[:-4]+"AUC_combined.ftr") for file in all_files], os.path.join(results_dir, "summary_combined.ftr"))

        col1, _, col2, col3, col4 = st.columns(5)
        num_cols = col1.number_input("show columns", 1, 5, 1)
        col3.markdown("##")
        if col3.button("Download Selection", help="Select a folder where data from selceted samples and chromatograms gets stored."):
            new_folder = get_dir()
            if new_folder:
                for file in all_files+["summary.ftr", "summary_combined.ftr"]:
                    df = pd.read_feather(os.path.join(results_dir, file))
                    path = os.path.join(new_folder, file[:-4])
                    df.to_csv(path+".tsv", sep="\t", index=False)
                col3.success("Download done!")

        df_summary_combined = pd.read_feather(os.path.join(results_dir, "summary_combined.ftr"))
        df_summary_combined.index = df_summary_combined["index"]
        df_summary_combined = df_summary_combined.drop(columns=["index"])
        col4.markdown("##")
        col4.download_button("Download Quantification Data", df_summary_combined.rename(columns={col: col+".mzML" for col in df_summary_combined.columns if col != "metabolite"}).to_csv(sep="\t", index=False), "Feature-Quantification-Targeted-Metabolomics.tsv")
        col4.download_button("Download Meta Data", pd.DataFrame({"filename": [file.replace("ftr", "mzML") for file in all_files], "ATTRIBUTE_Sample_Type": ["Sample"]*len(all_files)}).to_csv(sep="\t", index=False), "Meta-Data-Targeted-Metabolomics.tsv")


        st.markdown("***")
        st.markdown("Summary with combined intensities")
        fig = Plot().FeatureMatrix(df_summary_combined)
        st.plotly_chart(fig)
        st.dataframe(df_summary_combined)
        st.markdown("***")
        st.markdown("Summary with adduct intensities")
        df_summary = pd.read_feather(os.path.join(results_dir, "summary.ftr"))
        df_summary.index = df_summary["index"]
        df_summary = df_summary.drop(columns=["index"])
        fig = Plot().FeatureMatrix(df_summary)
        st.plotly_chart(fig)
        st.dataframe(df_summary)
        st.markdown("***")
        cols = st.columns(num_cols)
        while all_files:
            for col in cols:
                try:
                    file = all_files.pop()
                except IndexError:
                    break
                df_chrom = pd.read_feather(os.path.join(results_dir, file))
                df_auc = pd.read_feather(os.path.join(results_dir, file[:-4]+"AUC.ftr")).drop(columns=["index"])
                df_auc_combined = pd.read_feather(os.path.join(results_dir, file[:-4]+"AUC_combined.ftr")).drop(columns=["index"])

                fig_chrom, fig_auc, fig_auc_combined = Plot().FFMID(df_chrom, df_auc=df_auc, df_auc_combined=df_auc_combined, time_unit=time_unit, title=file[:-4])
                col.plotly_chart(fig_chrom)
                col.plotly_chart(fig_auc)
                col.dataframe(df_auc)
                col.plotly_chart(fig_auc_combined)
                col.dataframe(df_auc_combined)

                col.markdown("***")